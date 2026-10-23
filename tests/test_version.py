"""
Test the git-based versioning system.

Verifies:
- the version string follows the semantic format
- the resolution order (git -> VERSION file -> unknown)
- the parsing of `git describe` output
- the version is stamped in the PNG metadata and in the sidecar
- the release helper bumps versions with the semantic policy
"""

import json
import os
import re
import subprocess
import sys

import pytest

from utils import version as v


# ── Format ──────────────────────────────────────────────────────────────────

SEMVER_LOCAL = re.compile(
    r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)


def test_version_is_semver_with_build_metadata():
    """The version must be a valid semantic version."""
    current = v.get_version()
    assert SEMVER_LOCAL.match(current), f"'{current}' is not a valid semver string"


def test_version_info_has_all_the_fields():
    """The info dict must expose everything the banner and the stamp need."""
    info = v.get_version_info()
    for key in ("version", "base_version", "major", "minor", "patch",
                "prerelease", "build", "commit", "commits", "dirty",
                "tag", "source"):
        assert key in info, f"missing key: {key}"


def test_version_info_is_cached():
    """Two calls must return the same object (the cache works)."""
    first = v.get_version_info()
    second = v.get_version_info()
    assert first is second


def test_force_bypasses_the_cache():
    """force=True must recompute the value."""
    v.get_version_info()
    refreshed = v.get_version_info(force=True)
    assert refreshed["version"] == v.get_version()


def test_base_version_has_no_build_metadata():
    """The base version must be a plain semver."""
    base = v.get_base_version()
    assert "+" not in base, base
    assert SEMVER_LOCAL.match(base), base


def test_format_version_line():
    """The banner line must mention the version."""
    line = v.format_version_line()
    assert "Version:" in line
    assert v.get_version() in line


# ── Parsing of `git describe` ───────────────────────────────────────────────

@pytest.mark.parametrize("raw,expected_tag,expected_count,expected_commit,expected_dirty", [
    ("v2.0.0-21-gd8477fc", "v2.0.0", 21, "d8477fc", False),
    ("v2.0.0-21-gd8477fc-dirty", "v2.0.0", 21, "d8477fc", True),
    ("v2.0.0-0-gabc1234", "v2.0.0", 0, "abc1234", False),
    ("2.0.0-3-g0123abc", "2.0.0", 3, "0123abc", False),
    ("v2.1.0-rc.1-3-gabc1234", "v2.1.0-rc.1", 3, "abc1234", False),
])
def test_describe_parsing(raw, expected_tag, expected_count, expected_commit, expected_dirty):
    """The describe output must be parsed correctly."""
    match = v._DESCRIBE_RE.match(raw)
    assert match, f"'{raw}' did not match"
    assert match.group("tag") == expected_tag
    assert int(match.group("count")) == expected_count
    assert match.group("hash") == expected_commit
    assert (match.group("dirty") is not None) == expected_dirty


def test_build_info_format():
    """The build metadata must follow <count>.g<hash>[.dirty]."""
    assert v._build_info("2.0.0", 21, "d8477fc", False) == "2.0.0+21.gd8477fc"
    assert v._build_info("2.0.0", 21, "d8477fc", True) == "2.0.0+21.gd8477fc.dirty"


# ── The VERSION file fallback ───────────────────────────────────────────────

def test_version_file_exists_and_is_valid():
    """The committed VERSION file must hold a valid semver."""
    content = v._read_version_file()
    assert content is not None, "VERSION file is missing"
    assert v._SEMVER_RE.match(content), content


def test_fallback_to_version_file(monkeypatch, tmp_path):
    """Without git the VERSION file must be used."""
    version_file = tmp_path / "VERSION"
    version_file.write_text("9.9.9\n", encoding="utf-8")

    monkeypatch.setattr(v, "VERSION_FILE", str(version_file))
    monkeypatch.setattr(v, "_run_git", lambda *a, **k: None)
    monkeypatch.setattr(v, "_cache", None)

    info = v.get_version_info()
    assert info["source"] == "file"
    assert info["version"] == "9.9.9"
    assert info["base_version"] == "9.9.9"


def test_unknown_fallback(monkeypatch, tmp_path):
    """Without git and without the file the version must be the unknown one."""
    monkeypatch.setattr(v, "VERSION_FILE", str(tmp_path / "nope"))
    monkeypatch.setattr(v, "_run_git", lambda *a, **k: None)
    monkeypatch.setattr(v, "_cache", None)

    info = v.get_version_info()
    assert info["source"] == "unknown"
    assert info["version"] == v.UNKNOWN_VERSION


# ── The version is stamped in the files ─────────────────────────────────────

def _fake_image():
    import numpy as np

    class _Cpu:
        def numpy(self):
            return np.zeros((4, 4, 3), dtype=np.float32)

    class _Img:
        shape = (4, 4, 3)

        def cpu(self):
            return _Cpu()

    return [_Img()]


def test_version_stamped_in_png_and_sidecar(tmp_path):
    """The node must stamp the version in the PNG and in the sidecar."""
    import types
    from PIL import Image

    fp = types.ModuleType("folder_paths")
    fp.get_full_path = lambda c, n: None
    fp.get_folder_paths = lambda c: []
    sys.modules.setdefault("folder_paths", fp)

    from nodes.save_with_checkpoint import SaveImageWithCheckpoint

    node = SaveImageWithCheckpoint()
    node.save_images(
        images=_fake_image(),
        checkpoint_name="krea2.safetensors",
        filename_prefix="arte",
        prompt=None,
        extra_pnginfo=None,
        custom_path=str(tmp_path),
        enable_txt_file=True,
        enable_json_file=True,
    )

    pngs = [f for f in os.listdir(tmp_path) if f.endswith(".png")]
    with Image.open(os.path.join(tmp_path, pngs[0])) as img:
        info = img.info

    assert "node_version" in info, f"PNG keys: {list(info.keys())}"
    assert info["node_version"] == v.get_version()
    assert "node_version_info" in info
    assert json.loads(info["node_version_info"])["version"] == v.get_version()

    txts = [f for f in os.listdir(tmp_path) if f.endswith(".txt")]
    with open(os.path.join(tmp_path, txts[0]), encoding="utf-8") as fh:
        content = fh.read()
    assert f"node_version: {v.get_version()}" in content, content


def test_version_stamp_can_be_disabled(tmp_path):
    """stamp_version=False must leave the version out."""
    import types
    from PIL import Image

    fp = types.ModuleType("folder_paths")
    fp.get_full_path = lambda c, n: None
    fp.get_folder_paths = lambda c: []
    sys.modules.setdefault("folder_paths", fp)

    from nodes.save_with_checkpoint import SaveImageWithCheckpoint

    node = SaveImageWithCheckpoint()
    node.save_images(
        images=_fake_image(),
        checkpoint_name="krea2.safetensors",
        filename_prefix="arte",
        prompt=None,
        extra_pnginfo=None,
        custom_path=str(tmp_path),
        enable_txt_file=False,
        enable_json_file=False,
        stamp_version=False,
    )

    pngs = [f for f in os.listdir(tmp_path) if f.endswith(".png")]
    with Image.open(os.path.join(tmp_path, pngs[0])) as img:
        info = img.info
    assert "node_version" not in info, f"PNG keys: {list(info.keys())}"


# ── The release helper ──────────────────────────────────────────────────────

def test_bump_policy():
    """major / minor / patch must follow the semantic policy."""
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from tools.release import bump

    assert bump("2.0.0", "patch") == "2.0.1"
    assert bump("2.0.0", "minor") == "2.1.0"
    assert bump("2.0.0", "major") == "3.0.0"
    assert bump("2.9.9", "patch") == "2.9.10"
    assert bump("1.2.3", "major") == "2.0.0"


def test_bump_rejects_invalid_version():
    """An invalid version must be rejected."""
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from tools.release import bump

    with pytest.raises(SystemExit):
        bump("not-a-version", "patch")


def test_release_helper_show_runs():
    """`release.py show` must work."""
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = subprocess.run(
        [sys.executable, os.path.join(repo, "tools", "release.py"), "show"],
        capture_output=True, text=True, cwd=repo,
    )
    assert result.returncode == 0, result.stderr
    assert "VERSION file" in result.stdout
    assert "git describe" in result.stdout
