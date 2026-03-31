"""Unit tests for the preference detection classifier."""

import pytest

from neo4j_agent_memory.mcp._preference_detector import (
    DetectedPreference,
    PreferenceDetector,
)


@pytest.fixture
def detector():
    return PreferenceDetector()


class TestPositivePreferences:
    """Tests for detecting positive preference statements."""

    def test_i_like(self, detector):
        results = detector.detect("I like Italian food")
        assert len(results) == 1
        assert results[0].sentiment == "positive"
        assert "Italian food" in results[0].preference

    def test_i_love(self, detector):
        results = detector.detect("I love programming in Python")
        assert len(results) == 1
        assert results[0].sentiment == "positive"
        assert "programming in Python" in results[0].preference

    def test_i_really_enjoy(self, detector):
        results = detector.detect("I really enjoy hiking in the mountains")
        assert len(results) == 1
        assert results[0].sentiment == "positive"

    def test_i_prefer(self, detector):
        results = detector.detect("I prefer dark mode over light mode")
        assert len(results) == 1
        assert results[0].sentiment == "positive"

    def test_my_favorite_is(self, detector):
        results = detector.detect("My favorite color is blue")
        assert len(results) == 1
        assert results[0].sentiment == "positive"
        assert results[0].confidence >= 0.85

    def test_im_a_fan_of(self, detector):
        results = detector.detect("I'm a big fan of jazz music")
        assert len(results) == 1
        assert results[0].sentiment == "positive"

    def test_i_always_go_for(self, detector):
        results = detector.detect("I always go for the window seat on flights")
        assert len(results) == 1
        assert results[0].sentiment == "positive"


class TestNegativePreferences:
    """Tests for detecting negative preference statements."""

    def test_i_dont_like(self, detector):
        results = detector.detect("I don't like spicy food")
        assert len(results) == 1
        assert results[0].sentiment == "negative"
        assert "spicy food" in results[0].preference

    def test_i_hate(self, detector):
        results = detector.detect("I hate waking up early")
        assert len(results) == 1
        assert results[0].sentiment == "negative"

    def test_im_not_a_fan(self, detector):
        results = detector.detect("I'm not a fan of country music")
        assert len(results) == 1
        assert results[0].sentiment == "negative"

    def test_i_cant_stand(self, detector):
        results = detector.detect("I can't stand loud noises")
        assert len(results) == 1
        assert results[0].sentiment == "negative"

    def test_i_never_like(self, detector):
        results = detector.detect("I never like going to crowded places")
        assert len(results) == 1
        assert results[0].sentiment == "negative"


class TestCategoryInference:
    """Tests for automatic category inference from context."""

    def test_food_category(self, detector):
        results = detector.detect("I love sushi and Japanese cuisine")
        assert len(results) == 1
        assert results[0].category == "food"

    def test_music_category(self, detector):
        results = detector.detect("I prefer jazz music to classical")
        assert len(results) == 1
        assert results[0].category == "music"

    def test_technology_category(self, detector):
        results = detector.detect("I love programming in Python")
        assert len(results) == 1
        assert results[0].category == "technology"

    def test_entertainment_category(self, detector):
        results = detector.detect("I really enjoy watching Netflix shows")
        assert len(results) == 1
        assert results[0].category == "entertainment"

    def test_general_category_fallback(self, detector):
        results = detector.detect("I like warm blankets on cold nights")
        assert len(results) == 1
        assert results[0].category == "general"


class TestEdgeCases:
    """Tests for edge cases and non-preference text."""

    def test_no_preference_in_question(self, detector):
        results = detector.detect("Do you like Italian food?")
        assert len(results) == 0

    def test_no_preference_in_factual_statement(self, detector):
        results = detector.detect("The weather is nice today")
        assert len(results) == 0

    def test_short_text_ignored(self, detector):
        results = detector.detect("I like it")
        # "it" is <= 2 chars so filtered out
        assert len(results) == 0

    def test_empty_text(self, detector):
        results = detector.detect("")
        assert len(results) == 0

    def test_multiple_sentences(self, detector):
        text = "I love Italian food. The weather is nice. I hate waiting in line."
        results = detector.detect(text)
        assert len(results) == 2
        sentiments = {r.sentiment for r in results}
        assert "positive" in sentiments
        assert "negative" in sentiments

    def test_trailing_clause_removed(self, detector):
        results = detector.detect("I love pasta because my grandmother made it")
        assert len(results) == 1
        # "because..." clause should be stripped
        assert "because" not in results[0].preference

    def test_preference_subject_length_capped(self, detector):
        long_subject = "a " * 200
        results = detector.detect(f"I love {long_subject}")
        if results:
            assert len(results[0].preference) <= 200

    def test_one_match_per_sentence(self, detector):
        # Even if multiple patterns could match, only one should fire per sentence
        results = detector.detect("I love and enjoy Italian food")
        assert len(results) <= 1


class TestDetectedPreferenceModel:
    """Tests for the DetectedPreference dataclass."""

    def test_has_expected_fields(self):
        pref = DetectedPreference(
            category="food",
            preference="Italian cuisine",
            sentiment="positive",
            confidence=0.85,
            source_text="I love Italian cuisine",
        )
        assert pref.category == "food"
        assert pref.preference == "Italian cuisine"
        assert pref.sentiment == "positive"
        assert pref.confidence == 0.85
        assert pref.source_text == "I love Italian cuisine"
