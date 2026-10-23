"""
Scaffolding test for comfyui-model-rotation.
Verifies that node modules can be imported under stubbed ComfyUI environment
and have the expected RETURN_TYPES.
"""

import pytest


def test_checkpoint_rotation_imports():
    """With stubs installed, CheckpointRotationNode can be imported and has correct RETURN_TYPES."""
    # The node imports folder_paths and comfy.sd inside methods, but also at class level
    # we need the stubs to be present when the module loads (or we patch after).
    # Since the node does `import folder_paths` inside methods, the module-level
    # stub in conftest should be enough for import to succeed.
    from nodes.checkpoint_rotation import CheckpointRotationNode

    assert CheckpointRotationNode.RETURN_TYPES == ("MODEL", "CLIP", "VAE", "STRING", "STRING"), (
        f"Unexpected RETURN_TYPES: {CheckpointRotationNode.RETURN_TYPES}"
    )
    assert CheckpointRotationNode.RETURN_NAMES == ("model", "clip", "vae", "checkpoint_name", "info"), (
        f"Unexpected RETURN_NAMES: {CheckpointRotationNode.RETURN_NAMES}"
    )
    assert CheckpointRotationNode.FUNCTION == "load_checkpoint_rotated", (
        f"Unexpected FUNCTION: {CheckpointRotationNode.FUNCTION}"
    )
    assert CheckpointRotationNode.CATEGORY == "loaders", (
        f"Unexpected CATEGORY: {CheckpointRotationNode.CATEGORY}"
    )


def test_checkpoint_utils_imports():
    """CheckpointUtils can be imported and has expected methods."""
    from utils.checkpoint_utils import CheckpointUtils

    # Verify core methods exist
    assert hasattr(CheckpointUtils, "scan_checkpoint_folder"), "Missing scan_checkpoint_folder"
    assert hasattr(CheckpointUtils, "filter_checkpoints"), "Missing filter_checkpoints"
    assert hasattr(CheckpointUtils, "select_checkpoint_by_rotation"), "Missing select_checkpoint_by_rotation"
    assert hasattr(CheckpointUtils, "get_checkpoint_name_for_comfyui"), "Missing get_checkpoint_name_for_comfyui"
    assert hasattr(CheckpointUtils, "SUPPORTED_EXTENSIONS"), "Missing SUPPORTED_EXTENSIONS"


def test_path_utils_imports():
    """PathUtils can be imported and has expected methods."""
    from utils.path_utils import PathUtils

    assert hasattr(PathUtils, "get_checkpoints_base_path"), "Missing get_checkpoints_base_path"
    assert hasattr(PathUtils, "validate_subfolder"), "Missing validate_subfolder"
    assert hasattr(PathUtils, "get_relative_path"), "Missing get_relative_path"


def test_model_discovery_not_yet():
    """Placeholder: model_discovery module will be created in Task 2."""
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])