"""``__version__`` must match the ``[project] version`` in ``pyproject.toml``.

The two are maintained by hand and nothing reads one against the other, so
they could drift silently. That matters at release time: ``uv build`` takes the
*pyproject* value, so a tag cut from a bumped ``__version__`` alone builds an
artifact under the old number — and ``publish-python.yml`` only finds out when
PyPI rejects the upload as a duplicate, after the build job has already
reported success.

The version is read with a regex rather than :mod:`tomllib`, which does not
exist on Python 3.10 — the floor the unit suite still runs on.
"""

from __future__ import annotations

import re
from pathlib import Path

import neo4j_agent_memory

PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"

#: The ``[project]`` table only, so a ``version`` key in any other table
#: (a tool section, an optional-dependency group) cannot be picked up instead.
_PROJECT_TABLE_RE = re.compile(r"^\[project\]$(?P<body>.*?)^\[", re.MULTILINE | re.DOTALL)
_VERSION_RE = re.compile(r'^version\s*=\s*"(?P<version>[^"]+)"', re.MULTILINE)


def _pyproject_version() -> str:
    assert PYPROJECT.is_file(), f"expected a pyproject.toml at {PYPROJECT}"
    table = _PROJECT_TABLE_RE.search(PYPROJECT.read_text(encoding="utf-8"))
    assert table is not None, "no [project] table found in pyproject.toml"
    version = _VERSION_RE.search(table.group("body"))
    assert version is not None, "no version key found in the [project] table"
    return version.group("version")


def test_dunder_version_matches_pyproject() -> None:
    declared = _pyproject_version()
    assert neo4j_agent_memory.__version__ == declared, (
        f"__version__ is {neo4j_agent_memory.__version__!r} but pyproject.toml declares "
        f"{declared!r}; bump both or the published artifact carries the pyproject value"
    )
