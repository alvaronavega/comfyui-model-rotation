"""
Test the gitflow aware versioning.

Verifies:
- each branch type produces the right prerelease label
- main keeps the plain release version
- an unknown branch keeps the plain git describe version
"""

import pytest

from utils import version as v


# ── The branch → version mapping ────────────────────────────────────────────

def test_main_keeps_the_release_version():
    """On main the version is the release version itself."""
    assert v._branch_version("2.0.0", "main", 0) is None
    assert v._branch_version("2.0.0", "master", 0) is None


def test_develop_uses_the_next_minor():
    """develop carries the next minor as a dev prerelease."""
    assert v._branch_version("2.0.0", "develop", 5) == "2.1.0-dev.5"
    assert v._branch_version("2.0.0", "develop", 0) == "2.1.0-dev.0"
    assert v._branch_version("2.1.3", "develop", 2) == "2.2.0-dev.2"


def test_feature_branch():
    """feature/<name> carries the branch name."""
    assert v._branch_version("2.0.0", "feature/add-foo", 2) == "2.1.0-feature.add-foo.2"
    assert v._branch_version("2.0.0", "feature/x", 1) == "2.1.0-feature.x.1"


def test_feature_branch_name_is_sanitized():
    """The branch name must become a valid version fragment."""
    result = v._branch_version("2.0.0", "feature/meu recurso/ Legal", 1)
    assert result == "2.1.0-feature.meu.recurso.Legal.1", result
    # No character that would break the version string
    assert all(c.isalnum() or c in ".-" for c in result)

def test_release_branch_uses_the_release_version():
    """release/<version> carries the explicit version."""
    assert v._branch_version("2.0.0", "release/2.1.0", 1) == "2.1.0-rc.1"
    assert v._branch_version("2.0.0", "release/3.0.0", 4) == "3.0.0-rc.4"


def test_hotfix_branch_uses_the_next_patch():
    """hotfix/<name> carries the next patch."""
    assert v._branch_version("2.0.0", "hotfix/fix-bar", 1) == "2.0.1-hotfix.fix-bar.1"
    assert v._branch_version("2.1.3", "hotfix/x", 0) == "2.1.4-hotfix.x.0"


def test_unknown_branch_has_no_suffix():
    """An unknown branch keeps the plain version."""
    assert v._branch_version("2.0.0", "some/random-branch", 3) is None
    assert v._branch_version("2.0.0", "wip", 3) is None


# ── Helpers ─────────────────────────────────────────────────────────────────

def test_next_minor_and_patch():
    """The helpers must do the arithmetic."""
    assert v._next_minor("2.0.0") == "2.1.0"
    assert v._next_minor("2.9.9") == "2.10.0"
    assert v._next_patch("2.0.0") == "2.0.1"
    assert v._next_patch("2.0.9") == "2.0.10"


# ── The produced versions are valid ─────────────────────────────────────────

@pytest.mark.parametrize("branch,expected", [
    ("develop", True),
    ("feature/add-foo", True),
    ("release/2.1.0", True),
    ("hotfix/fix-bar", True),
])
def test_branch_versions_are_valid_semver(branch, expected):
    """Every branch version must be a valid semantic version."""
    version = v._branch_version("2.0.0", branch, 3)
    assert version is not None
    assert v._SEMVER_RE.match(version), version


def test_branch_version_is_exposed_in_the_info():
    """The info dict must carry the branch name."""
    info = v.get_version_info()
    assert "branch" in info
