"""Tests for the documentation build pipeline.

These tests verify that the Antora build system works correctly.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def npm_installed(docs_root: Path) -> bool:
    """Ensure npm dependencies are installed."""
    node_modules = docs_root / "node_modules"
    if not node_modules.exists():
        result = subprocess.run(
            ["npm", "install"],
            cwd=docs_root,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            pytest.skip(f"npm install failed: {result.stderr}")
    return True


@pytest.fixture(scope="module")
def antora_site_dir(docs_root: Path) -> Path:
    """Get the Antora build output directory."""
    return docs_root / "build" / "site"


@pytest.fixture(scope="module")
def antora_component_dir(antora_site_dir: Path) -> Path:
    """Get the Antora component output directory (agent-memory)."""
    return antora_site_dir / "agent-memory"


@pytest.mark.docs
class TestBuildScriptExists:
    """Test that required build files exist."""

    def test_antora_playbook_exists(self, docs_root: Path):
        """Verify antora-playbook.yml exists."""
        playbook = docs_root / "antora-playbook.yml"
        assert playbook.exists(), "antora-playbook.yml not found in docs directory"

    def test_antora_component_exists(self, docs_root: Path):
        """Verify antora.yml component descriptor exists."""
        antora_yml = docs_root / "antora.yml"
        assert antora_yml.exists(), "antora.yml not found in docs directory"

    def test_package_json_exists(self, docs_root: Path):
        """Verify package.json exists."""
        package_json = docs_root / "package.json"
        assert package_json.exists(), "package.json not found in docs directory"

    def test_favicon_exists(self, docs_root: Path):
        """Verify favicon exists."""
        favicon = docs_root / "assets" / "favicon.svg"
        assert favicon.exists(), "assets/favicon.svg not found"


@pytest.mark.docs
class TestNpmCommands:
    """Test npm commands work correctly."""

    def test_npm_install_succeeds(self, docs_root: Path):
        """Verify npm install works."""
        result = subprocess.run(
            ["npm", "install"],
            cwd=docs_root,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, f"npm install failed: {result.stderr}"

    def test_npm_build_succeeds(self, docs_root: Path, npm_installed: bool):
        """Verify npm run build works."""
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=docs_root,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, f"npm run build failed: {result.stderr}"


@pytest.mark.docs
class TestBuildOutput:
    """Test that build produces expected output."""

    @pytest.fixture(autouse=True)
    def ensure_built(self, docs_root: Path, npm_installed: bool):
        """Ensure docs are built before these tests."""
        subprocess.run(
            ["npm", "run", "build"],
            cwd=docs_root,
            capture_output=True,
            text=True,
            timeout=120,
        )

    def test_site_directory_created(self, antora_site_dir: Path):
        """Verify build/site directory is created."""
        assert antora_site_dir.exists(), "build/site directory not created"
        assert antora_site_dir.is_dir(), "build/site is not a directory"

    def test_component_directory_created(self, antora_component_dir: Path):
        """Verify agent-memory component directory is created."""
        assert antora_component_dir.exists(), "agent-memory component directory not created"

    def test_index_html_created(self, antora_component_dir: Path):
        """Verify index.html is created."""
        index_html = antora_component_dir / "index.html"
        assert index_html.exists(), "index.html not created in agent-memory/"

    def test_quadrant_directories_created(self, antora_component_dir: Path):
        """Verify Diataxis quadrant directories are created."""
        quadrants = ["tutorials", "how-to", "reference", "explanation"]
        for quadrant in quadrants:
            quadrant_dir = antora_component_dir / quadrant
            assert quadrant_dir.exists(), f"{quadrant}/ directory not created"
            index_html = quadrant_dir / "index.html"
            assert index_html.exists(), f"{quadrant}/index.html not created"

    def test_all_adoc_files_converted(
        self, docs_dir: Path, antora_component_dir: Path, all_adoc_files: list[Path]
    ):
        """Verify each .adoc file has a corresponding .html file."""
        missing = []
        for adoc_file in all_adoc_files:
            # Skip nav.adoc as it's not converted to HTML
            if adoc_file.name == "nav.adoc":
                continue
            try:
                relative = adoc_file.relative_to(docs_dir)
                # HTML files are in component directory
                html_file = antora_component_dir / relative.with_suffix(".html")
                if not html_file.exists():
                    missing.append(str(relative))
            except ValueError:
                # File is outside docs_dir
                continue

        assert not missing, f"Missing HTML files for: {missing}"


@pytest.mark.docs
class TestHtmlContent:
    """Test that generated HTML has expected content."""

    @pytest.fixture(autouse=True)
    def ensure_built(self, docs_root: Path, npm_installed: bool):
        """Ensure docs are built before these tests."""
        subprocess.run(
            ["npm", "run", "build"],
            cwd=docs_root,
            capture_output=True,
            text=True,
            timeout=120,
        )

    def test_index_has_navigation(self, antora_component_dir: Path):
        """Verify index.html has navigation elements."""
        index_html = antora_component_dir / "index.html"
        content = index_html.read_text()

        # Antora UI bundle includes navigation
        assert "nav" in content.lower(), "Navigation not found in index.html"

    def test_pages_have_breadcrumbs(self, antora_component_dir: Path):
        """Verify nested pages have breadcrumb navigation."""
        tutorial_index = antora_component_dir / "tutorials" / "index.html"
        if tutorial_index.exists():
            content = tutorial_index.read_text()
            assert "breadcrumb" in content.lower(), "Breadcrumbs not found in tutorials/index.html"

    def test_code_blocks_have_highlighting(self, antora_component_dir: Path):
        """Verify code blocks have syntax highlighting classes."""
        # Check a file known to have code blocks
        tutorial = antora_component_dir / "tutorials" / "first-agent-memory.html"
        if tutorial.exists():
            content = tutorial.read_text()
            # Antora/highlight.js adds highlight classes
            assert "highlight" in content or "code" in content, "Syntax highlighting not found"

    def test_pages_have_search(self, antora_component_dir: Path):
        """Verify pages reference search functionality."""
        index_html = antora_component_dir / "index.html"
        content = index_html.read_text()
        # Neo4j UI bundle includes search
        assert "search" in content.lower(), "Search not found in index.html"


@pytest.mark.docs
class TestBuildPerformance:
    """Test build performance characteristics."""

    def test_build_completes_in_reasonable_time(self, docs_root: Path, npm_installed: bool):
        """Verify build completes within timeout."""
        import time

        start = time.time()
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=docs_root,
            capture_output=True,
            text=True,
            timeout=120,
        )
        elapsed = time.time() - start

        assert result.returncode == 0, f"Build failed: {result.stderr}"
        # Antora builds are typically fast but allow more time for CI
        assert elapsed < 60, f"Build took too long: {elapsed:.1f}s (expected < 60s)"

    def test_build_completes_successfully(self, docs_root: Path, npm_installed: bool):
        """Verify build completes without fatal errors."""
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=docs_root,
            capture_output=True,
            text=True,
            timeout=120,
        )

        assert result.returncode == 0, f"Build failed with return code {result.returncode}"
        # Check stderr for FATAL errors (warnings are OK)
        assert "FATAL" not in result.stderr, f"Build had fatal errors: {result.stderr}"
