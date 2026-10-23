"""
Gitflow helper for comfyui-model-rotation.

``git flow`` is not installed on every machine, so this script implements the
same workflow with plain git calls:

    main       production, only tagged releases
    develop    integration branch
    feature/*  new features, branched from develop
    release/*  release preparation, branched from develop
    hotfix/*   urgent fixes, branched from main

Usage::

    python tools/gitflow.py status
    python tools/gitflow.py feature add-foo
    python tools/gitflow.py release 2.1.0
    python tools/gitflow.py hotfix fix-bar
    python tools/gitflow.py finish feature/add-foo
    python tools/gitflow.py start develop
    python tools/gitflow.py check

``finish`` merges according to the branch type:

* feature/*  -> develop  (fast forward when possible)
* release/*  -> main (tagged) and develop
* hotfix/*   -> main (tagged) and develop
"""

import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

MAIN_BRANCH = "main"
DEVELOP_BRANCH = "develop"

BRANCH_TYPES = ("feature/", "release/", "hotfix/")


def run_git(args, check=True, capture=True):
    """Run a git command inside the repository."""
    result = subprocess.run(
        ["git"] + args,
        cwd=REPO,
        capture_output=capture,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        message = (result.stderr or "").strip() if capture else ""
        sys.stderr.write(message + "\n")
        raise SystemExit(result.returncode)
    return result


def git_out(args) -> str:
    """Return the trimmed stdout of a git command."""
    return (run_git(args).stdout or "").strip()


def current_branch() -> str:
    """Return the current branch name."""
    name = git_out(["rev-parse", "--abbrev-ref", "HEAD"])
    return name or "HEAD"


def branch_exists(name: str) -> bool:
    """True when the branch exists locally."""
    return run_git(["rev-parse", "-q", "--verify", f"refs/heads/{name}"],
                   check=False).returncode == 0


def remote_exists(name: str) -> bool:
    """True when the branch exists on the remote."""
    return run_git(["ls-remote", "--heads", "origin", name],
                   check=False).returncode == 0 and bool(
        git_out(["ls-remote", "--heads", "origin", name]))


def is_clean() -> bool:
    """True when there are no uncommitted changes."""
    return git_out(["status", "--porcelain"]) == ""


def ensure_base_branch(name: str) -> None:
    """Make sure *name* exists locally, creating it from main when missing."""
    if branch_exists(name):
        return
    print(f"creating {name} from {MAIN_BRANCH}")
    run_git(["branch", name, MAIN_BRANCH])


def cmd_status(args) -> int:
    """Show the state of every branch of the flow."""
    print(f"repository : {REPO}")
    print(f"current    : {current_branch()}")
    print(f"clean tree : {'yes' if is_clean() else 'NO — uncommitted changes'}")
    print()
    print("branches:")
    for line in git_out(["branch", "-vv"]).splitlines():
        print(f"  {line}")
    print()
    print("flow state:")
    for name in (MAIN_BRANCH, DEVELOP_BRANCH):
        if branch_exists(name):
            ahead = git_out(["rev-list", "--count", f"{name}..HEAD"]) or "0"
            behind = git_out(["rev-list", "--count", f"HEAD..{name}"]) or "0"
            print(f"  {name:<10} ahead {ahead} / behind {behind}")
        else:
            print(f"  {name:<10} (missing)")
    print()
    print("next steps:")
    print(f"  python tools/gitflow.py feature <name>     # new feature from {DEVELOP_BRANCH}")
    print(f"  python tools/gitflow.py release <version>  # release prep")
    print(f"  python tools/gitflow.py hotfix <name>      # urgent fix from {MAIN_BRANCH}")
    return 0


def cmd_start(args) -> int:
    """Switch to an existing branch of the flow."""
    name = args.branch
    if not branch_exists(name):
        print(f"branch '{name}' does not exist locally")
        return 1
    run_git(["checkout", name])
    print(f"switched to {name}")
    return 0


def cmd_feature(args) -> int:
    """Create a feature branch from develop."""
    if not is_clean():
        print("refusing: the working tree has uncommitted changes")
        return 1
    ensure_base_branch(DEVELOP_BRANCH)
    name = f"feature/{args.name}"
    if branch_exists(name):
        print(f"branch '{name}' already exists")
        return 1
    run_git(["checkout", DEVELOP_BRANCH])
    run_git(["checkout", "-b", name])
    print(f"created {name} from {DEVELOP_BRANCH}")
    print("when done: python tools/gitflow.py finish " + name)
    return 0


def cmd_release(args) -> int:
    """Create a release branch from develop."""
    if not is_clean():
        print("refusing: the working tree has uncommitted changes")
        return 1
    ensure_base_branch(DEVELOP_BRANCH)
    name = f"release/{args.version}"
    if branch_exists(name):
        print(f"branch '{name}' already exists")
        return 1
    run_git(["checkout", DEVELOP_BRANCH])
    run_git(["checkout", "-b", name])
    print(f"created {name} from {DEVELOP_BRANCH}")
    print("bump the version with: python tools/release.py set " + args.version)
    print("when done: python tools/gitflow.py finish " + name)
    return 0


def cmd_hotfix(args) -> int:
    """Create a hotfix branch from main."""
    if not is_clean():
        print("refusing: the working tree has uncommitted changes")
        return 1
    ensure_base_branch(MAIN_BRANCH)
    name = f"hotfix/{args.name}"
    if branch_exists(name):
        print(f"branch '{name}' already exists")
        return 1
    run_git(["checkout", MAIN_BRANCH])
    run_git(["checkout", "-b", name])
    print(f"created {name} from {MAIN_BRANCH}")
    print("when done: python tools/gitflow.py finish " + name)
    return 0


def cmd_finish(args) -> int:
    """Merge the current branch back, following the flow rules."""
    name = args.branch or current_branch()
    if not is_clean():
        print("refusing: the working tree has uncommitted changes")
        return 1
    if not branch_exists(name):
        print(f"branch '{name}' does not exist")
        return 1

    if name.startswith("feature/"):
        target = DEVELOP_BRANCH
        print(f"merging {name} into {target}")
        run_git(["checkout", target])
        run_git(["merge", "--no-ff", "-m", f"merge: {name}", name])
        run_git(["branch", "-d", name])
        print(f"done — {name} merged into {target} and deleted")
        print("publish with: git push origin " + target)
        return 0

    if name.startswith("release/"):
        version = name[len("release/"):]
        print(f"merging {name} into {MAIN_BRANCH}")
        run_git(["checkout", MAIN_BRANCH])
        run_git(["merge", "--no-ff", "-m", f"release: v{version}", name])
        tag = f"v{version}"
        if not branch_exists(tag) and run_git(["rev-parse", "-q", "--verify",
                                              f"refs/tags/{tag}"],
                                             check=False).returncode != 0:
            run_git(["tag", "-a", tag, "-m", f"Release {version}"])
            print(f"tag {tag} created")
        print(f"merging {MAIN_BRANCH} back into {DEVELOP_BRANCH}")
        run_git(["checkout", DEVELOP_BRANCH])
        run_git(["merge", "--no-ff", "-m", f"merge: {MAIN_BRANCH} into {DEVELOP_BRANCH}",
                 MAIN_BRANCH])
        run_git(["branch", "-d", name])
        print("done")
        print(f"publish with: git push origin {MAIN_BRANCH} {DEVELOP_BRANCH} {tag}")
        return 0

    if name.startswith("hotfix/"):
        print(f"merging {name} into {MAIN_BRANCH}")
        run_git(["checkout", MAIN_BRANCH])
        run_git(["merge", "--no-ff", "-m", f"hotfix: {name}", name])
        print(f"merging {MAIN_BRANCH} back into {DEVELOP_BRANCH}")
        run_git(["checkout", DEVELOP_BRANCH])
        run_git(["merge", "--no-ff", "-m", f"merge: {MAIN_BRANCH} into {DEVELOP_BRANCH}",
                 MAIN_BRANCH])
        run_git(["branch", "-d", name])
        print("done")
        print(f"publish with: git push origin {MAIN_BRANCH} {DEVELOP_BRANCH}")
        return 0

    print(f"'{name}' is not a flow branch (expected one of: {', '.join(BRANCH_TYPES)}*)")
    return 1


def cmd_check(args) -> int:
    """Check that the repository follows the flow rules."""
    problems = []

    if not branch_exists(MAIN_BRANCH):
        problems.append(f"the branch '{MAIN_BRANCH}' does not exist")
    if not branch_exists(DEVELOP_BRANCH):
        problems.append(f"the branch '{DEVELOP_BRANCH}' does not exist")

    tags = git_out(["tag", "-l"]).splitlines()
    if not tags:
        problems.append("there is no tag yet (run: python tools/release.py tag)")

    for branch in (MAIN_BRANCH, DEVELOP_BRANCH):
        if branch_exists(branch):
            status = git_out(["status", "--porcelain"])
            if status:
                problems.append(f"'{branch}' has uncommitted changes")

    if problems:
        print("flow problems found:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print("the flow looks good")
    print(f"  {MAIN_BRANCH}   : {git_out(['rev-parse', '--short', MAIN_BRANCH])}")
    print(f"  {DEVELOP_BRANCH:<8}: {git_out(['rev-parse', '--short', DEVELOP_BRANCH])}")
    print(f"  tags     : {', '.join(tags) or '(none)'}")
    return 0


def cmd_init(args) -> int:
    """Turn the current branch into main and create develop."""
    current = current_branch()
    if current != MAIN_BRANCH:
        print(f"renaming '{current}' to '{MAIN_BRANCH}'")
        run_git(["branch", "-m", MAIN_BRANCH])
    if not branch_exists(DEVELOP_BRANCH):
        print(f"creating '{DEVELOP_BRANCH}' from '{MAIN_BRANCH}'")
        run_git(["branch", DEVELOP_BRANCH, MAIN_BRANCH])
    print()
    print("done. the flow is:")
    print(f"  {MAIN_BRANCH}    -> production (tagged releases)")
    print(f"  {DEVELOP_BRANCH} -> integration")
    print("  feature/*  release/*  hotfix/*")
    print()
    print("publish with: git push origin --all --tags")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="gitflow.py",
        description="Gitflow helper for comfyui-model-rotation.",
    )
    sub = parser.add_subparsers(dest="command")

    p_status = sub.add_parser("status", help="show the state of the flow")
    p_status.set_defaults(func=cmd_status)

    p_check = sub.add_parser("check", help="check that the flow rules are respected")
    p_check.set_defaults(func=cmd_check)

    p_init = sub.add_parser("init", help="turn the current branch into main + create develop")
    p_init.set_defaults(func=cmd_init)

    p_start = sub.add_parser("start", help="switch to a branch")
    p_start.add_argument("branch")
    p_start.set_defaults(func=cmd_start)

    p_feature = sub.add_parser("feature", help="create a feature branch from develop")
    p_feature.add_argument("name")
    p_feature.set_defaults(func=cmd_feature)

    p_release = sub.add_parser("release", help="create a release branch from develop")
    p_release.add_argument("version")
    p_release.set_defaults(func=cmd_release)

    p_hotfix = sub.add_parser("hotfix", help="create a hotfix branch from main")
    p_hotfix.add_argument("name")
    p_hotfix.set_defaults(func=cmd_hotfix)

    p_finish = sub.add_parser("finish", help="merge the branch back")
    p_finish.add_argument("branch", nargs="?", default=None)
    p_finish.set_defaults(func=cmd_finish)

    args = parser.parse_args()
    if not getattr(args, "func", None):
        args = parser.parse_args(["status"])
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
