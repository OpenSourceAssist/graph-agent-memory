"""Validate one fresh Antora build; no implicit installs or stale build output."""

from pathlib import Path

import pytest

from scripts.check_docs import build_site, rendered_report


@pytest.fixture(scope="session")
def built_docs(tmp_path_factory, project_root):
    executable = project_root / "docs/node_modules/.bin/antora"
    assert executable.exists(), "Install docs dependencies first: cd docs && npm ci"
    destination = tmp_path_factory.mktemp("antora") / "site"
    log, errors = build_site(destination, root=project_root)
    (destination.parent / "build.log").write_text(log)
    assert not errors, "\n".join(errors) + "\nFull build output:\n" + log
    return destination


@pytest.mark.docs
def test_all_pages_render(built_docs: Path, docs_dir: Path):
    component = built_docs / "agent-memory"
    missing = [
        str(p.relative_to(docs_dir))
        for p in docs_dir.rglob("*.adoc")
        if not (component / p.relative_to(docs_dir).with_suffix(".html")).exists()
    ]
    assert not missing, f"Missing rendered pages: {missing}"


@pytest.mark.docs
def test_rendered_content_links_fragments_and_images(built_docs: Path):
    report = rendered_report(built_docs)
    assert report["content_links"] > 0
    assert not report["errors"], "\n".join(report["errors"])


@pytest.mark.docs
def test_entry_has_navigation_and_content(built_docs: Path):
    html = (built_docs / "agent-memory/index.html").read_text()
    assert '<article class="doc"' in html
    assert "<nav" in html
    assert "tutorials/" in html and "reference/" in html
