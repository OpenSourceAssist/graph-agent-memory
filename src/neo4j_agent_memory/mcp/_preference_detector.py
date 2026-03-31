"""Lightweight pattern-based preference detection from user messages.

Identifies preference statements like "I love Italian food" or "I don't
like spicy things" and extracts them with a category and sentiment.

This is a rule-based classifier, not an LLM-based one. It trades recall
for zero latency and zero API cost, making it suitable for fire-and-forget
background processing after every user message.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ── Detected preference model ────────────────────────────────────────


@dataclass
class DetectedPreference:
    """A preference detected from user text."""

    category: str
    """Inferred category (e.g., 'food', 'technology', 'general')."""

    preference: str
    """The preference statement, cleaned up from the matched text."""

    sentiment: str
    """'positive' or 'negative'."""

    confidence: float
    """Detection confidence (0.0-1.0). Pattern matches are 0.7-0.9."""

    source_text: str
    """The original sentence that triggered detection."""


# ── Category keywords ─────────────────────────────────────────────────

_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "food": [
        "food",
        "eat",
        "cook",
        "restaurant",
        "cuisine",
        "dish",
        "meal",
        "breakfast",
        "lunch",
        "dinner",
        "snack",
        "pizza",
        "pasta",
        "sushi",
        "coffee",
        "tea",
        "beer",
        "wine",
        "chocolate",
        "dessert",
        "vegan",
        "vegetarian",
        "spicy",
        "sweet",
        "salty",
        "flavor",
    ],
    "music": [
        "music",
        "song",
        "band",
        "artist",
        "album",
        "genre",
        "playlist",
        "concert",
        "jazz",
        "rock",
        "pop",
        "classical",
        "hip-hop",
        "rap",
        "listen",
        "spotify",
    ],
    "technology": [
        "tech",
        "software",
        "hardware",
        "app",
        "programming",
        "language",
        "framework",
        "python",
        "javascript",
        "rust",
        "react",
        "linux",
        "mac",
        "windows",
        "android",
        "ios",
        "ai",
        "machine learning",
        "dark mode",
        "light mode",
        "editor",
        "ide",
        "vim",
        "emacs",
    ],
    "entertainment": [
        "movie",
        "film",
        "show",
        "series",
        "book",
        "novel",
        "game",
        "gaming",
        "tv",
        "netflix",
        "podcast",
        "youtube",
        "anime",
        "manga",
        "comic",
        "theater",
        "theatre",
    ],
    "travel": [
        "travel",
        "trip",
        "vacation",
        "country",
        "city",
        "beach",
        "mountain",
        "flight",
        "hotel",
        "destination",
        "hiking",
    ],
    "communication": [
        "email",
        "message",
        "chat",
        "call",
        "meeting",
        "slack",
        "verbose",
        "concise",
        "brief",
        "detailed",
        "formal",
        "casual",
        "tone",
        "style",
    ],
    "work": [
        "work",
        "job",
        "career",
        "office",
        "remote",
        "meeting",
        "schedule",
        "deadline",
        "project",
        "team",
        "manager",
    ],
}

# ── Preference patterns ───────────────────────────────────────────────

# Each pattern: (compiled_regex, sentiment, confidence)
# Group 1 should capture the preference subject/object.
_POSITIVE_PATTERNS: list[tuple[re.Pattern[str], float]] = [
    (re.compile(r"\bi (?:really )?(?:like|love|enjoy|adore|prefer)\s+(.+)", re.I), 0.85),
    (
        re.compile(
            r"\bi(?:'m| am) (?:a (?:big )?fan of|into|passionate about|interested in)\s+(.+)", re.I
        ),
        0.80,
    ),
    (
        re.compile(
            r"\bmy (?:favorite|favourite|preferred|go-to)(?: \w+)? (?:is|are|would be)\s+(.+)", re.I
        ),
        0.90,
    ),
    (
        re.compile(
            r"\bi (?:always|usually|tend to|often) (?:go for|choose|pick|use|opt for)\s+(.+)", re.I
        ),
        0.75,
    ),
    (re.compile(r"\bnothing (?:beats|compares to|is better than)\s+(.+)", re.I), 0.80),
    (
        re.compile(r"\bi(?:'m| am) (?:a|an) (\w+(?:\s+\w+)?) (?:person|kind of person|type)", re.I),
        0.75,
    ),
]

_NEGATIVE_PATTERNS: list[tuple[re.Pattern[str], float]] = [
    (
        re.compile(
            r"\bi (?:don't|do not|don't|never|can't stand|cannot stand) (?:like|enjoy|want|care for)\s+(.+)",
            re.I,
        ),
        0.85,
    ),
    (re.compile(r"\bi (?:hate|dislike|detest|loathe|despise|avoid)\s+(.+)", re.I), 0.85),
    (re.compile(r"\bi(?:'m| am) not (?:a fan of|into|fond of|keen on)\s+(.+)", re.I), 0.80),
    (re.compile(r"\bi (?:can't|cannot) (?:stand|tolerate|bear)\s+(.+)", re.I), 0.85),
    (
        re.compile(
            r"\b(\w+(?:\s+\w+)?) (?:is|are) (?:the worst|terrible|awful|horrible|overrated)", re.I
        ),
        0.70,
    ),
]


# ── Detector class ────────────────────────────────────────────────────


class PreferenceDetector:
    """Detects preference statements in user text using regex patterns.

    Not meant to be exhaustive -- favors precision over recall. Better to
    miss some preferences than to create false positives in the knowledge graph.
    """

    def detect(self, text: str) -> list[DetectedPreference]:
        """Detect preferences in text.

        Splits text into sentences and checks each against preference patterns.

        Args:
            text: User message text.

        Returns:
            List of detected preferences (may be empty).
        """
        sentences = _split_sentences(text)
        preferences: list[DetectedPreference] = []

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue

            # Check positive patterns
            for pattern, confidence in _POSITIVE_PATTERNS:
                match = pattern.search(sentence)
                if match:
                    subject = _clean_subject(match.group(1))
                    if subject and len(subject) > 2:
                        category = _infer_category(sentence)
                        preferences.append(
                            DetectedPreference(
                                category=category,
                                preference=subject,
                                sentiment="positive",
                                confidence=confidence,
                                source_text=sentence,
                            )
                        )
                    break  # One match per sentence

            else:
                # Check negative patterns (only if no positive match)
                for pattern, confidence in _NEGATIVE_PATTERNS:
                    match = pattern.search(sentence)
                    if match:
                        subject = _clean_subject(match.group(1))
                        if subject and len(subject) > 2:
                            category = _infer_category(sentence)
                            preferences.append(
                                DetectedPreference(
                                    category=category,
                                    preference=subject,
                                    sentiment="negative",
                                    confidence=confidence,
                                    source_text=sentence,
                                )
                            )
                        break

        return preferences


# ── Helpers ───────────────────────────────────────────────────────────


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences using basic punctuation rules."""
    # Split on sentence-ending punctuation followed by space or end
    parts = re.split(r"(?<=[.!?])\s+", text)
    # Also split on newlines
    sentences: list[str] = []
    for part in parts:
        sentences.extend(part.split("\n"))
    return [s for s in sentences if s.strip()]


def _clean_subject(raw: str) -> str:
    """Clean up the captured preference subject."""
    # Remove trailing punctuation and common filler
    cleaned = raw.strip().rstrip(".,!?;:")
    # Remove trailing clauses like "because..." or "when..."
    cleaned = re.split(
        r"\b(?:because|when|since|but|although|though|so|and)\b", cleaned, maxsplit=1
    )[0].strip()
    # Remove trailing punctuation again after clause removal
    cleaned = cleaned.rstrip(".,!?;:")
    # Cap length
    if len(cleaned) > 200:
        cleaned = cleaned[:200].rsplit(" ", 1)[0]
    return cleaned


def _infer_category(sentence: str) -> str:
    """Infer the preference category from sentence content."""
    lower = sentence.lower()
    best_category = "general"
    best_score = 0

    for category, keywords in _CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in lower)
        if score > best_score:
            best_score = score
            best_category = category

    return best_category
