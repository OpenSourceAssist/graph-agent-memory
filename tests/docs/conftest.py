"""Pytest fixtures for documentation tests."""

from __future__ import annotations

from pathlib import Path

import pytest


def get_project_root() -> Path:
    """Get the project root directory."""
    # tests/docs/conftest.py -> project_root
    return Path(__file__).parent.parent.parent


def get_docs_dir() -> Path:
    """Get the docs directory."""
    return get_project_root() / "docs"


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Fixture providing the project root directory."""
    return get_project_root()


@pytest.fixture(scope="session")
def docs_dir() -> Path:
    """Fixture providing the docs directory."""
    docs = get_docs_dir()
    if not docs.exists():
        pytest.skip("Docs directory not found")
    return docs


@pytest.fixture(scope="session")
def site_dir(docs_dir: Path) -> Path:
    """Fixture providing the built _site directory."""
    return docs_dir / "_site"


@pytest.fixture(scope="session")
def all_adoc_files(docs_dir: Path) -> list[Path]:
    """Fixture providing all AsciiDoc files in docs."""
    files = []
    for adoc_file in docs_dir.rglob("*.adoc"):
        # Skip node_modules and _site
        if "node_modules" in str(adoc_file) or "_site" in str(adoc_file):
            continue
        files.append(adoc_file)
    return sorted(files)


@pytest.fixture(scope="session")
def quadrant_dirs(docs_dir: Path) -> dict[str, Path]:
    """Fixture providing paths to Diataxis quadrant directories."""
    return {
        "tutorials": docs_dir / "tutorials",
        "how-to": docs_dir / "how-to",
        "reference": docs_dir / "reference",
        "explanation": docs_dir / "explanation",
    }


@pytest.fixture(scope="session")
def python_snippets(docs_dir: Path):
    """Fixture providing all Python code snippets from docs."""
    from tests.docs.utils import extract_python_snippets

    return extract_python_snippets(docs_dir)


@pytest.fixture(scope="session")
def complete_snippets(python_snippets):
    """Fixture providing only complete (runnable) Python snippets."""
    return [s for s in python_snippets if s.is_complete]
