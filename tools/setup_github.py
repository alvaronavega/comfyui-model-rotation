"""
Configure the GitHub repository for the gitflow workflow.

Applies, in order:

1. ``main`` becomes the default branch
2. the leftover ``claude/...`` branch is deleted
3. branch protection on ``main`` and ``develop``:
   * no direct push (a pull request is required)
   * the CI must pass before merging
   * one approval is required
   * no force push, no branch deletion
   * the branch must be up to date before merging

Usage::

    gh auth login
    python tools/setup_github.py

    # see what would be done, without doing it
    python tools/setup_github.py --dry-run
"""

import argparse
import json
import subprocess
import sys

REPO_SLUG = "alvaronavega/comfyui-model-rotation"
OLD_BRANCH = "claude/comfyui-checkpoint-rotation-node-011CUpNy5JrP8K5cTBn1UjMH"
PROTECTED = ("main", "develop")
CI_WORKFLOW = "ci.yml"


def gh(args, dry_run=False, check=True):
    """Run a gh command."""
    if dry_run:
        print(f"    [dry-run] gh {' '.join(args)}")
        return None
    result = subprocess.run(
        ["gh"] + args,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 and check:
        sys.stderr.write((result.stderr or result.stdout or "gh failed").strip() + "\n")
        raise SystemExit(result.returncode)
    return result


def gh_json(args, dry_run=False):
    """Run a gh command and parse its JSON output."""
    if dry_run:
        print(f"    [dry-run] gh {' '.join(args)}")
        return None
    result = gh(args)
    try:
        return json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return {}


def check_auth(dry_run=False):
    """Make sure the gh CLI is logged in."""
    if dry_run:
        return True
    result = subprocess.run(
        ["gh", "auth", "status"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print("the gh CLI is not logged in.")
        print("run:  gh auth login")
        print("then:  python tools/setup_github.py")
        return False
    return True


def set_default_branch(dry_run=False):
    """Make main the default branch of the repository."""
    print("[1/3] setting 'main' as the default branch")
    gh([
        "api", "--method", "PATCH",
        f"repos/{REPO_SLUG}",
        "-f", "default_branch=main",
    ], dry_run=dry_run)


def delete_old_branch(dry_run=False):
    """Delete the leftover claude/... branch."""
    print("[2/3] deleting the leftover branch")
    result = gh_json(
        ["api", f"repos/{REPO_SLUG}/git/refs/heads/{OLD_BRANCH}"],
        dry_run=dry_run,
    )
    if dry_run:
        return
    if not result:
        print("    (it does not exist anymore)")
        return
    gh([
        "api", "--method", "DELETE",
        f"repos/{REPO_SLUG}/git/refs/heads/{OLD_BRANCH}",
    ], dry_run=dry_run)
    print(f"    deleted {OLD_BRANCH}")


def protection_payload(branch: str) -> str:
    """Build the branch protection payload for *branch*."""
    payload = {
        "required_status_checks": {
            "strict": True,
            "contexts": [CI_WORKFLOW],
        },
        "enforce_admins": False,
        "required_pull_request_reviews": {
            "dismiss_stale_reviews": True,
            "require_code_owner_reviews": False,
            "required_approving_review_count": 1,
        },
        "restrictions": None,
        "required_linear_history": False,
        "allow_force_pushes": False,
        "allow_deletions": False,
        "required_conversation_resolution": True,
        "block_creations": False,
        "lock_branch": False,
        "allow_fork_syncing": True,
    }
    return json.dumps(payload)


def protect_branches(dry_run=False):
    """Apply the branch protection rules."""
    print("[3/3] protecting the branches")
    for branch in PROTECTED:
        print(f"    -> {branch}")
        gh([
            "api", "--method", "PUT",
            f"repos/{REPO_SLUG}/branches/{branch}/protection",
            "--input", "-",
        ], dry_run=dry_run)


def show_status(dry_run=False):
    """Print the current protection state."""
    print("current state:")
    repo = gh_json(["api", f"repos/{REPO_SLUG}"], dry_run=dry_run)
    if repo:
        print(f"    default branch : {repo.get('default_branch')}")
    for branch in PROTECTED:
        result = gh_json(
            ["api", f"repos/{REPO_SLUG}/branches/{branch}/protection"],
            dry_run=dry_run,
        )
        state = "protected" if result else "NOT protected"
        print(f"    {branch:<10}: {state}")


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="setup_github.py",
        description="Configure the GitHub repository for the gitflow workflow.",
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="print what would be done without doing it")
    parser.add_argument("--status", action="store_true",
                        help="only show the current state")
    args = parser.parse_args()

    print(f"repository: {REPO_SLUG}\n")

    if args.status:
        show_status(args.dry_run)
        return 0

    if not check_auth(args.dry_run):
        return 1

    set_default_branch(args.dry_run)
    delete_old_branch(args.dry_run)
    protect_branches(args.dry_run)

    print()
    show_status(args.dry_run)
    print()
    print("done. the flow is ready:")
    print("  main        protected, pull request + green CI required")
    print("  develop     protected, pull request + green CI required")
    print("  feature/*   open, merged into develop")
    print("  release/*   open, merged into main (tagged) and develop")
    print("  hotfix/*    open, merged into main and develop")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
