"""
Version resolution for comfyui-model-rotation.

The version of the package is derived from the git history, so it always
tells you exactly which code produced an image.  The resolution order is:

1. ``git describe --tags --long --dirty`` inside the package folder
   -> ``2.0.0+21.gd8477fc`` (release + commits since the tag + short hash)
   -> ``2.0.0+21.gd8477fc.dirty`` when the working tree has changes
   -> ``2.0.0`` when the checkout sits exactly on a clean tag
2. the committed ``VERSION`` file, when git is not available
   (a ZIP download has no ``.git`` folder)
3. ``0.0.0+unknown`` as the last resort

The result is a Semantic Version string with the build metadata carrying the
commit information.  It is also a valid PEP 440 local version, so it can be
used as a Python package version if the project is ever packaged.

Examples::

    2.0.0                 exactly on the tag v2.0.0, clean tree
    2.0.0+21.gd8477fc      21 commits after v2.0.0
    2.0.0+21.gd8477fc.dirty  ... and the working tree has uncommitted changes
    2.1.0-rc.1+3.gabc1234  a prerelease tag
"""

import os
import re
import subprocess
from typing import Any, Dict, Optional

#: Folder that holds the package (the parent of ``utils/``)
PACKAGE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Committed file with the last released version, used when git is missing
VERSION_FILE = os.path.join(PACKAGE_ROOT, "VERSION")

#: Used when neither git nor the VERSION file can be used
UNKNOWN_VERSION = "0.0.0+unknown"

#: ``git describe --tags --long --dirty`` output
#:   v2.0.0-21-gd8477fc[-dirty]
_DESCRIBE_RE = re.compile(
    r"^(?P<tag>.+?)-(?P<count>\d+)-g(?P<hash>[0-9a-fA-F]+)(?P<dirty>-dirty)?$"
)

#: A plain semantic version
_SEMVER_RE = re.compile(
    r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?:-(?P<pre>[0-9A-Za-z.-]+))?"
    r"(?:\+(?P<build>[0-9A-Za-z.-]+))?$"
)

# Cache: the version never changes while the process is running
_cache: Optional[Dict[str, Any]] = None


def _run_git(args: list, cwd: str) -> Optional[str]:
    """Run a git command and return its stdout, or None when it fails."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    out = (result.stdout or "").strip()
    return out or None


def _read_version_file(path: Optional[str] = None) -> Optional[str]:
    """Read the committed VERSION file.

    The path defaults to the module level ``VERSION_FILE`` and is resolved at
    call time (not at import time), so it can be pointed somewhere else.
    """
    if path is None:
        path = VERSION_FILE
    try:
        with open(path, "r", encoding="utf-8") as fh:
            value = fh.read().strip()
    except (OSError, UnicodeDecodeError):
        return None
    return value or None


def _split_semver(version: str) -> Dict[str, Any]:
    """Split a semantic version into its parts."""
    match = _SEMVER_RE.match(version)
    if not match:
        return {
            "major": 0, "minor": 0, "patch": 0,
            "prerelease": None, "build": None,
        }
    return {
        "major": int(match.group("major")),
        "minor": int(match.group("minor")),
        "patch": int(match.group("patch")),
        "prerelease": match.group("pre"),
        "build": match.group("build"),
    }


def _build_info(base: str, count: int, commit: str, dirty: bool) -> str:
    """Assemble the build metadata part of the version string."""
    parts = [str(count), f"g{commit}"]
    if dirty:
        parts.append("dirty")
    return f"{base}+{'.'.join(parts)}"


def _current_branch() -> Optional[str]:
    """Return the current branch name, or None when detached."""
    name = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], PACKAGE_ROOT)
    if not name or name == "HEAD":
        return None
    return name


def _next_minor(base: str) -> str:
    """Return the next minor version of *base* (2.0.0 -> 2.1.0)."""
    parts = _split_semver(base)
    return f"{parts['major']}.{parts['minor'] + 1}.0"


def _next_patch(base: str) -> str:
    """Return the next patch version of *base* (2.0.0 -> 2.0.1)."""
    parts = _split_semver(base)
    return f"{parts['major']}.{parts['minor']}.{parts['patch'] + 1}"


def _branch_version(base: str, branch: str, commits: int) -> Optional[str]:
    """Return the version suffix implied by *branch* (gitflow aware).

    * ``main`` / ``master``      -> the release version itself
    * ``develop``                -> ``2.1.0-dev.<commits>``
    * ``feature/<name>``         -> ``2.1.0-feature.<name>.<commits>``
    * ``release/<version>``      -> ``<version>-rc.<commits>``
    * ``hotfix/<name>``          -> ``2.0.1-hotfix.<name>.<commits>``
    """
    if branch in ("main", "master"):
        return None  # the plain release version

    if branch == "develop":
        return f"{_next_minor(base)}-dev.{commits}"

    if branch.startswith("feature/"):
        name = branch[len("feature/"):].strip() or "feature"
        name = re.sub(r"[^0-9A-Za-z.]+", ".", name).strip(".")
        return f"{_next_minor(base)}-feature.{name}.{commits}"

    if branch.startswith("release/"):
        version = branch[len("release/"):].strip() or base
        return f"{version}-rc.{commits}"

    if branch.startswith("hotfix/"):
        name = branch[len("hotfix/"):].strip() or "hotfix"
        name = re.sub(r"[^0-9A-Za-z.]+", ".", name).strip(".")
        return f"{_next_patch(base)}-hotfix.{name}.{commits}"

    return None


def get_version_info(force: bool = False) -> Dict[str, Any]:
    """Return the full version information.

    Returns:
        A dict with the keys:

        * ``version``     – the full version string
        * ``base_version`` – the release version without the build metadata
        * ``major`` / ``minor`` / ``patch`` – the numeric parts
        * ``prerelease``  – the prerelease label, or None
        * ``commit``      – the short commit hash, or None
        * ``commits``     – commits since the tag, or None
        * ``dirty``       – True when the working tree has changes
        * ``tag``         – the raw tag name, or None
        * ``source``      – ``"git"``, ``"file"`` or ``"unknown"``
    """
    global _cache
    if _cache is not None and not force:
        return _cache

    info: Dict[str, Any] = {
        "version": UNKNOWN_VERSION,
        "base_version": "0.0.0",
        "major": 0, "minor": 0, "patch": 0,
        "prerelease": None, "build": None,
        "commit": None, "commits": None,
        "dirty": False, "tag": None,
        "branch": None,
        "source": "unknown",
    }

    # 1) git describe
    raw = _run_git(["describe", "--tags", "--long", "--dirty"], PACKAGE_ROOT)
    if raw:
        match = _DESCRIBE_RE.match(raw)
        if match:
            tag = match.group("tag")
            count = int(match.group("count"))
            commit = match.group("hash")
            dirty = match.group("dirty") is not None
            base = tag[1:] if tag.startswith("v") else tag

            if count == 0 and not dirty:
                version = base
            else:
                version = _build_info(base, count, commit, dirty)

            info.update({
                "version": version,
                "base_version": base,
                "commit": commit,
                "commits": count,
                "dirty": dirty,
                "tag": tag,
                "source": "git",
            })
            info.update(_split_semver(version))

            # 1c) gitflow: the branch decides the prerelease label
            branch = _current_branch()
            info["branch"] = branch
            branch_version = _branch_version(base, branch, count) if branch else None
            if branch_version:
                info["version"] = branch_version
                info.update(_split_semver(branch_version))

            _cache = info
            return info

    # 1b) git is there but there is no tag yet: fall back to the commit hash
    raw_hash = _run_git(["rev-parse", "--short", "HEAD"], PACKAGE_ROOT)
    if raw_hash:
        base = _read_version_file() or "0.0.0"
        dirty = _run_git(["status", "--porcelain"], PACKAGE_ROOT) not in (None, "")
        version = _build_info(base, 0, raw_hash, dirty)
        info.update({
            "version": version,
            "base_version": base,
            "commit": raw_hash,
            "commits": 0,
            "dirty": dirty,
            "tag": None,
            "source": "git",
        })
        info.update(_split_semver(version))
        _cache = info
        return info

    # 2) the committed VERSION file (ZIP install, no git)
    base = _read_version_file()
    if base:
        info.update({
            "version": base,
            "base_version": base,
            "source": "file",
        })
        info.update(_split_semver(base))
        _cache = info
        return info

    # 3) nothing at all
    _cache = info
    return info


def get_version() -> str:
    """Return the full version string (cached)."""
    return get_version_info()["version"]


def get_base_version() -> str:
    """Return the release version without the build metadata (e.g. ``2.0.0``)."""
    return get_version_info()["base_version"]


def get_version_dict() -> Dict[str, Any]:
    """Return a copy of the version information."""
    return dict(get_version_info())


def format_version_line() -> str:
    """Return a one line summary, handy for the console banner."""
    info = get_version_info()
    line = f"Version: {info['version']}"
    if info.get("tag"):
        line += f"  (tag: {info['tag']})"
    if info.get("commit"):
        line += f"  (commit: {info['commit']})"
    if info.get("dirty"):
        line += "  [UNCOMMITTED CHANGES]"
    return line


__all__ = [
    "get_version",
    "get_base_version",
    "get_version_info",
    "get_version_dict",
    "format_version_line",
    "PACKAGE_ROOT",
    "VERSION_FILE",
    "UNKNOWN_VERSION",
]
