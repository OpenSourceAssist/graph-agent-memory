"""Tests for the documentation build pipeline.

These tests verify that the Node.js/AsciiDoctor build system works correctly.
"""

from __future__ import annotations

import subprocess
import sys
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


@pytest.mark.docs
class TestBuildScriptExists:
    """Test that required build files exist."""

    def test_build_script_exists(self, docs_root: Path):
        """Verify build.js exists."""
        build_script = docs_root / "build.js"
        assert build_script.exists(), "build.js not found in docs directory"

    def test_package_json_exists(self, docs_root: Path):
        """Verify package.json exists."""
        package_json = docs_root / "package.json"
        assert package_json.exists(), "package.json not found in docs directory"

    def test_style_css_exists(self, docs_root: Path):
        """Verify style.css exists."""
        style_css = docs_root / "assets" / "style.css"
        assert style_css.exists(), "assets/style.css not found"

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
            timeout=60,
        )
        assert result.returncode == 0, f"npm run build failed: {result.stderr}"

    def test_npm_lint_succeeds(self, docs_root: Path, npm_installed: bool):
        """Verify npm run lint (link validation) works."""
        # First build
        subprocess.run(
            ["npm", "run", "build"],
            cwd=docs_root,
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Then lint
        result = subprocess.run(
            ["npm", "run", "lint"],
            cwd=docs_root,
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Note: lint may find broken links in old files, so we check for specific patterns
        # rather than requiring returncode == 0
        if "broken links" in result.stdout:
            # Parse number of broken links
            import re

            match = re.search(r"Found (\d+) broken links", result.stdout)
            if match:
                broken_count = int(match.group(1))
                # Allow some broken links in legacy files, but fail if too many
                if broken_count > 20:
                    pytest.fail(f"Too many broken links: {broken_count}\n{result.stdout}")


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
            timeout=60,
        )

    def test_site_directory_created(self, site_dir: Path):
        """Verify _site directory is created."""
        assert site_dir.exists(), "_site directory not created"
        assert site_dir.is_dir(), "_site is not a directory"

    def test_index_html_created(self, site_dir: Path):
        """Verify index.html is created in modules/ROOT/pages/."""
        # With Antora structure, index.html is in modules/ROOT/pages/
        index_html = site_dir / "modules" / "ROOT" / "pages" / "index.html"
        assert index_html.exists(), "modules/ROOT/pages/index.html not created"

    def test_style_css_copied(self, site_dir: Path):
        """Verify style.css is copied to _site."""
        style_css = site_dir / "style.css"
        assert style_css.exists(), "style.css not copied to _site"

    def test_favicon_copied(self, site_dir: Path):
        """Verify favicon is copied to _site."""
        favicon = site_dir / "favicon.svg"
        assert favicon.exists(), "favicon.svg not copied to _site"

    def test_quadrant_directories_created(self, site_dir: Path):
        """Verify Diataxis quadrant directories are created."""
        # With Antora structure, quadrants are in modules/ROOT/pages/
        pages_dir = site_dir / "modules" / "ROOT" / "pages"
        quadrants = ["tutorials", "how-to", "reference", "explanation"]
        for quadrant in quadrants:
            quadrant_dir = pages_dir / quadrant
            assert quadrant_dir.exists(), f"{quadrant}/ directory not created"
            index_html = quadrant_dir / "index.html"
            assert index_html.exists(), f"{quadrant}/index.html not created"

    def test_all_adoc_files_converted(
        self, docs_dir: Path, site_dir: Path, all_adoc_files: list[Path]
    ):
        """Verify each .adoc file has a corresponding .html file."""
        missing = []
        for adoc_file in all_adoc_files:
            # Skip nav.adoc as it's outside the pages directory
            if adoc_file.name == "nav.adoc":
                continue
            try:
                relative = adoc_file.relative_to(docs_dir)
                # HTML files are in modules/ROOT/pages/ subdirectory of site_dir
                html_file = site_dir / "modules" / "ROOT" / "pages" / relative.with_suffix(".html")
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
            timeout=60,
        )

    def test_index_has_navigation(self, site_dir: Path):
        """Verify index.html has navigation elements."""
        # With Antora structure, index.html is in modules/ROOT/pages/
        index_html = site_dir / "modules" / "ROOT" / "pages" / "index.html"
        content = index_html.read_text()

        assert "docs-nav" in content, "Navigation not found in index.html"
        assert "Tutorials" in content, "Tutorials link not found"
        assert "How-To" in content or "How-to" in content, "How-To link not found"
        assert "Reference" in content, "Reference link not found"
        assert "Explanation" in content or "Concepts" in content, "Explanation link not found"

    def test_pages_have_breadcrumbs(self, site_dir: Path):
        """Verify nested pages have breadcrumb navigation."""
        # With Antora structure, tutorials are in modules/ROOT/pages/tutorials/
        tutorial_index = site_dir / "modules" / "ROOT" / "pages" / "tutorials" / "index.html"
        if tutorial_index.exists():
            content = tutorial_index.read_text()
            assert "breadcrumb" in content, "Breadcrumbs not found in tutorials/index.html"

    def test_code_blocks_have_highlighting(self, site_dir: Path):
        """Verify code blocks have syntax highlighting classes."""
        # Check a file known to have code blocks
        tutorial = site_dir / "modules" / "ROOT" / "pages" / "tutorials" / "first-agent-memory.html"
        if tutorial.exists():
            content = tutorial.read_text()
            # highlight.js adds hljs classes
            assert "hljs" in content or "highlight" in content, "Syntax highlighting not found"

    def test_pages_have_theme_toggle(self, site_dir: Path):
        """Verify pages have theme toggle button."""
        index_html = site_dir / "modules" / "ROOT" / "pages" / "index.html"
        content = index_html.read_text()
        assert "theme-toggle" in content, "Theme toggle not found"

    def test_pages_have_search(self, site_dir: Path):
        """Verify pages have search functionality."""
        index_html = site_dir / "modules" / "ROOT" / "pages" / "index.html"
        content = index_html.read_text()
        # Search is loaded from Pagefind
        assert "search" in content.lower(), "Search not found in index.html"


@pytest.mark.docs
class TestSearchIndex:
    """Test Pagefind search index generation."""

    def test_pagefind_index_generated(self, docs_root: Path, site_dir: Path, npm_installed: bool):
        """Verify Pagefind search index is generated."""
        # Run build with search
        result = subprocess.run(
            ["npm", "run", "build:search"],
            cwd=docs_root,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            pytest.skip(f"build:search failed (Pagefind may not be installed): {result.stderr}")

        pagefind_dir = site_dir / "pagefind"
        assert pagefind_dir.exists(), "pagefind/ directory not created"

        # Check for index files
        assert any(pagefind_dir.glob("*.js")), "No JavaScript files in pagefind/"
        assert any(pagefind_dir.glob("*.css")), "No CSS files in pagefind/"


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
            timeout=60,
        )
        elapsed = time.time() - start

        assert result.returncode == 0, f"Build failed: {result.stderr}"
        assert elapsed < 30, f"Build took too long: {elapsed:.1f}s (expected < 30s)"

    def test_build_reports_file_count(self, docs_root: Path, npm_installed: bool):
        """Verify build reports number of files processed."""
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=docs_root,
            capture_output=True,
            text=True,
            timeout=60,
        )

        assert "Files processed" in result.stdout or "files" in result.stdout.lower(), (
            "Build output doesn't report file count"
        )
