"""
Semantic version release helper for comfyui-model-rotation.

Bumps the committed ``VERSION`` file, creates the annotated git tag and
prints the commands to publish it.  The version that the package reports at
runtime comes from ``git describe`` (see ``utils/version.py``), so the tag is
what really defines a release.

Usage::

    python tools/release.py patch      # 2.0.0 -> 2.0.1
    python tools/release.py minor      # 2.0.0 -> 2.1.0
    python tools/release.py major      # 2.0.0 -> 3.0.0
    python tools/release.py set 2.5.0  # explicit version
    python tools/release.py show       # current state, no changes
    python tools/release.py tag        # re-tag the current commit

Policy (Semantic Versioning)
-----------------------------
MAJOR  a node class id is removed or renamed, a RETURN_TYPES changes, or the
       order of the widgets changes (existing graphs stop working)
MINOR  a new node, a new widget or a new option is added
PATCH  a bug fix, documentation, tests or an internal refactor
"""

import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
VERSION_FILE = os.path.join(REPO, "VERSION")

SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$")

BUMP_HELP = {
    "patch": "bug fix, documentation, tests or internal refactor",
    "minor": "new node, new widget or new option",
    "major": "breaking change (node id, RETURN_TYPES or widget order)",
}


def run_git(args, check=True):
    """Run a git command inside the repository."""
    result = subprocess.run(
        ["git"] + args,
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        sys.stderr.write(result.stderr or "git failed\n")
        raise SystemExit(result.returncode)
    return result


def git_output(args) -> str:
    """Return the trimmed stdout of a git command."""
    return (run_git(args).stdout or "").strip()


def read_version() -> str:
    """Read the committed VERSION file."""
    with open(VERSION_FILE, "r", encoding="utf-8") as fh:
        return fh.read().strip()


def write_version(version: str) -> None:
    """Write the VERSION file."""
    with open(VERSION_FILE, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(version + "\n")


def parse_version(version: str):
    """Split a version into (major, minor, patch, prerelease)."""
    match = SEMVER_RE.match(version)
    if not match:
        raise SystemExit(f"'{version}' is not a valid semantic version")
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)),
            match.group(4))


def bump(version: str, kind: str) -> str:
    """Return the next version for the given bump kind."""
    major, minor, patch, pre = parse_version(version)
    if kind == "major":
        return f"{major + 1}.0.0"
    if kind == "minor":
        return f"{major}.{minor + 1}.0"
    if kind == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise SystemExit(f"unknown bump '{kind}'")


def current_commit() -> str:
    """Return the short hash of HEAD."""
    return git_output(["rev-parse", "--short", "HEAD"])


def is_clean() -> bool:
    """True when there are no uncommitted changes."""
    return git_output(["status", "--porcelain"]) == ""


def describe() -> str:
    """Return the raw ``git describe`` output, or a message when it fails."""
    result = run_git(["describe", "--tags", "--long", "--dirty"], check=False)
    if result.returncode != 0:
        return "(no tag yet)"
    return (result.stdout or "").strip()


def tag_exists(tag: str) -> bool:
    """True when the tag already exists."""
    result = run_git(["rev-parse", "-q", "--verify", f"refs/tags/{tag}"], check=False)
    return result.returncode == 0


def cmd_show(args) -> int:
    """Show the current version state without changing anything."""
    version = read_version()
    print(f"VERSION file      : {version}")
    print(f"git describe      : {describe()}")
    print(f"HEAD commit       : {current_commit()}")
    print(f"working tree      : {'clean' if is_clean() else 'HAS CHANGES'}")
    print(f"latest tag        : {git_output(['describe', '--tags', '--abbrev=0']) if tag_exists('v' + version) else '(none for this version)'}")
    return 0


def cmd_tag(args) -> int:
    """Create the annotated tag for the current VERSION (no file change)."""
    version = read_version()
    tag = f"v{version}"
    if tag_exists(tag):
        print(f"tag '{tag}' already exists")
        return 1
    if not is_clean():
        print("refusing to tag: the working tree has uncommitted changes")
        return 1
    run_git(["tag", "-a", tag, "-m", f"Release {version}"])
    print(f"tag '{tag}' created on {current_commit()}")
    print()
    print("publish it with:")
    print(f"    git push origin {tag}")
    return 0


def cmd_release(args) -> int:
    """Bump the version, commit it and tag the result."""
    if not is_clean():
        print("refusing to release: the working tree has uncommitted changes")
        print("commit or stash them first")
        return 1

    current = read_version()
    if args.kind == "set":
        new_version = args.value
        parse_version(new_version)  # validate
    else:
        new_version = bump(current, args.kind)

    tag = f"v{new_version}"
    if tag_exists(tag):
        print(f"refusing to release: tag '{tag}' already exists")
        return 1

    print(f"current version   : {current}")
    print(f"new version       : {new_version}")
    if args.kind in BUMP_HELP:
        print(f"bump reason       : {args.kind} — {BUMP_HELP[args.kind]}")
    print()

    write_version(new_version)
    run_git(["add", "--", os.path.basename(VERSION_FILE)])

    # Make sure the file really got staged: a .gitignore entry would
    # otherwise make the release produce a tag without the version file.
    staged = git_output(["diff", "--cached", "--name-only"])
    if os.path.basename(VERSION_FILE) not in staged.splitlines():
        print(f"refusing to release: '{os.path.basename(VERSION_FILE)}' was not staged.")
        print("it is probably listed in .gitignore — the version file must be committed")
        print(f"(restore it with: git add -f {os.path.basename(VERSION_FILE)})")
        write_version(current)  # put the old value back
        return 1

    run_git(["commit", "-m", f"release: v{new_version}"])
    run_git(["tag", "-a", tag, "-m", f"Release {new_version}"])

    commit = current_commit()
    print(f"VERSION updated   : {new_version}")
    print(f"commit created    : {commit}")
    print(f"tag created       : {tag}")
    print()
    print("publish it with:")
    print(f"    git push origin {args.branch or 'HEAD'} {tag}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="release.py",
        description="Semantic version helper for comfyui-model-rotation.",
    )
    sub = parser.add_subparsers(dest="command")

    p_bump = sub.add_parser("patch", help="bug fix release")
    p_bump.set_defaults(func=cmd_release, kind="patch", value=None)

    p_minor = sub.add_parser("minor", help="new feature release")
    p_minor.set_defaults(func=cmd_release, kind="minor", value=None)

    p_major = sub.add_parser("major", help="breaking change release")
    p_major.set_defaults(func=cmd_release, kind="major", value=None)

    p_set = sub.add_parser("set", help="release an explicit version")
    p_set.add_argument("value", help="the new version, e.g. 2.5.0")
    p_set.set_defaults(func=cmd_release, kind="set")

    p_tag = sub.add_parser("tag", help="tag the current VERSION without bumping")
    p_tag.set_defaults(func=cmd_tag)

    p_show = sub.add_parser("show", help="show the current version state")
    p_show.set_defaults(func=cmd_show)

    args = parser.parse_args()
    if not getattr(args, "func", None):
        args = parser.parse_args(["show"])
    if not hasattr(args, "branch"):
        args.branch = None
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
