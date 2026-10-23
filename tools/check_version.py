"""
Check that the version resolves from the git history and that the nodes load.

Used by the CI (and handy locally).  It is a standalone script on purpose:
the workflow runs it on Windows too, where a bash heredoc would not work.

Exit code 0 means everything is fine.
"""

import os
import sys
import types

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)


def check_version():
    """The version must come from the git history."""
    from utils.version import get_version, get_version_info

    info = get_version_info()
    print("version :", info["version"])
    print("base    :", info["base_version"])
    print("commit  :", info["commit"])
    print("branch  :", info["branch"])
    print("source  :", info["source"])
    print()

    assert info["source"] == "git", f"the version did not come from git ({info['source']})"
    assert info["commit"], "no commit hash resolved"
    assert info["version"], "no version resolved"
    assert info["version"].startswith(info["base_version"]), \
        f"'{info['version']}' does not start with '{info['base_version']}'"
    return info


def check_nodes():
    """The nodes must import and carry the version and the credit."""
    # The nodes import folder_paths and comfy.sd from the ComfyUI runtime.
    # Outside ComfyUI we stub them.
    folder_paths = types.ModuleType("folder_paths")
    folder_paths.get_full_path = lambda category, name: None
    folder_paths.get_folder_paths = lambda category: []
    sys.modules.setdefault("folder_paths", folder_paths)

    from nodes.checkpoint_rotation import CheckpointRotationNode
    from nodes.rotation_with_counter import CheckpointRotationWithCounter
    from nodes.save_with_checkpoint import SaveImageWithCheckpoint
    from nodes.simple_rotation import SimpleCheckpointRotation
    from nodes.simple_rotation_direct import CheckpointRotationSimple
    from nodes.checkpoint_filename import CheckpointFilename
    from nodes.batch_counter import BatchIndexCounter, SimpleCounter
    from utils.version import get_version

    nodes = [
        CheckpointRotationNode,
        CheckpointRotationWithCounter,
        SaveImageWithCheckpoint,
        SimpleCheckpointRotation,
        CheckpointRotationSimple,
        CheckpointFilename,
        BatchIndexCounter,
        SimpleCounter,
    ]

    for node in nodes:
        assert node.VERSION == get_version(), f"{node.__name__}: wrong VERSION"
        assert node.AUTHOR == "Alvaro Navega", f"{node.__name__}: wrong AUTHOR"
        assert node.ORIGINAL_AUTHOR == "trunksn1", f"{node.__name__}: missing the original credit"
    print(f"{len(nodes)} nodes OK, version {get_version()}")


def main() -> int:
    try:
        check_version()
        check_nodes()
    except AssertionError as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print()
    print("everything checks out")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
