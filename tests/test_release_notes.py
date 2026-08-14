"""The version being packaged must have a changelog section, and the release job must find it.

The release workflow builds its GitHub Release body by running scripts/changelog_section.py. That
step runs after the upload to PyPI, because the upload is the irreversible part and it goes first,
which means a missing section is discovered when the version is already public and can no longer
be replaced. So the discovery is moved here, where it costs a red pull request instead.

It also enforces the rule at the top of CHANGELOG.md by construction: a version bump in
pyproject.toml with no line saying which figure moved cannot reach a tag.

The script is exercised as a subprocess rather than imported, because that is exactly how the
workflow calls it: the contract under test is the exit code and what lands on stdout.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "changelog_section.py"

# Read out of pyproject.toml and not out of importlib.metadata, which would answer with whatever
# was last installed and would pass on a bump nobody synced. Read with a regex and not with
# tomllib, which does not exist on 3.10, the floor this suite runs against.
VERSION_LINE = re.compile(r'^version\s*=\s*"(?P<version>[^"]+)"', re.MULTILINE)


def packaged_version() -> str:
    match = VERSION_LINE.search((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert match is not None, "pyproject.toml has no version line"
    return match.group("version")


def run(version: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT), version],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_the_packaged_version_has_release_notes() -> None:
    result = run(packaged_version())
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip(), "the section exists but is empty"


def test_the_notes_stop_at_the_next_version() -> None:
    """A section must not swallow the ones below it, or every release repeats the whole history."""
    body = run(packaged_version()).stdout
    assert "## [" not in body


def test_an_unknown_version_is_refused() -> None:
    """Refused, not answered with an empty body: a silent empty release note is the failure."""
    result = run("99.99.99")
    assert result.returncode == 1
    assert not result.stdout.strip()
