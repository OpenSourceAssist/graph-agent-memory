"""Pytest fixtures for documentation tests."""

from __future__ import annotations

from pathlib import Path

import pytest


def get_project_root() -> Path:
    """Get the project root directory."""
    # tests/docs/conftest.py -> project_root
    return Path(__file__).parent.parent.parent


def get_docs_root() -> Path:
    """Get the docs root directory (contains antora.yml)."""
    return get_project_root() / "docs"


def get_pages_dir() -> Path:
    """Get the Antora pages directory (contains content files)."""
    return get_docs_root() / "modules" / "ROOT" / "pages"


def get_module_root() -> Path:
    """Get the Antora module root (contains nav.adoc)."""
    return get_docs_root() / "modules" / "ROOT"


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Fixture providing the project root directory."""
    return get_project_root()


@pytest.fixture(scope="session")
def docs_dir() -> Path:
    """Fixture providing the docs pages directory (where content files live)."""
    pages = get_pages_dir()
    if not pages.exists():
        pytest.skip("Docs pages directory not found")
    return pages


@pytest.fixture(scope="session")
def docs_root() -> Path:
    """Fixture providing the docs root directory."""
    return get_docs_root()


@pytest.fixture(scope="session")
def site_dir() -> Path:
    """Fixture providing the built _site directory."""
    return get_docs_root() / "_site"


@pytest.fixture(scope="session")
def all_adoc_files(docs_dir: Path) -> list[Path]:
    """Fixture providing all AsciiDoc files in docs (pages + nav.adoc)."""
    files = []
    # Get all page files
    for adoc_file in docs_dir.rglob("*.adoc"):
        files.append(adoc_file)
    # Also include nav.adoc from module root
    nav_file = get_module_root() / "nav.adoc"
    if nav_file.exists():
        files.append(nav_file)
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
    """Fixture providing all Python code snippets from docs pages."""
    from tests.docs.utils import extract_python_snippets

    return extract_python_snippets(docs_dir)


@pytest.fixture(scope="session")
def complete_snippets(python_snippets):
    """Fixture providing only complete (runnable) Python snippets."""
    return [s for s in python_snippets if s.is_complete]
