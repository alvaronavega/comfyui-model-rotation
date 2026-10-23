"""
Test for the rewired CheckpointRotationNode.

Verifies:
- INPUT_TYPES includes model_folder as last optional widget
- load_checkpoint_rotated with diffusion mode returns (model, None, None, name, info)
- load_checkpoint_rotated with checkpoints mode returns (model, clip, vae, name, info) like today
- Empty discovery → raises ModelNotFoundError
- info string contains category hint
"""

import pytest
from unittest import mock

from utils.model_discovery import list_model_names, select_rotated, load_by_category, ModelNotFoundError


def test_node_input_types_include_model_folder():
    """Check that INPUT_TYPES includes model_folder as last optional widget."""
    from nodes.checkpoint_rotation import CheckpointRotationNode

    # Get the source of INPUT_TYPES and verify model_folder is in optional
    input_types = CheckpointRotationNode.INPUT_TYPES()
    optional_keys = list(input_types["optional"].keys())
    # model_folder should be the LAST optional key
    assert "model_folder" in optional_keys, "model_folder missing from INPUT_TYPES optional"
    # It should be after checkpoint_filter in the dict order
    filter_idx = optional_keys.index("checkpoint_filter")
    model_idx = optional_keys.index("model_folder")
    assert model_idx > filter_idx, (
        f"model_folder (idx {model_idx}) should come after checkpoint_filter (idx {filter_idx})"
    )


def test_load_checkpoint_rotated_diffusion_mode():
    """diffusion mode: returns (model, None, None, name, info) — clip and vae are None."""
    from nodes.checkpoint_rotation import CheckpointRotationNode

    # Set up stubbed filename_lists for diffusion_models
    from utils.model_discovery import filename_lists as _fl
    _fl["diffusion_models"] = ["krea2_unet_4.safetensors", "krea2_unet_5.safetensors"]

    # No need to patch checkpoint_cache — it's been removed from the node
    with mock.patch.object(CheckpointRotationNode, "IS_CHANGED", return_value=0.0):
        node = CheckpointRotationNode()

        # Call with diffusion model folder and select mode
        result = node.load_checkpoint_rotated(
            subfolder="",
            change_interval=1,
            batch_index=0,
            rotation_mode="sequential",
            seed=42,
            checkpoint_filter="",
            model_folder="diffusion_models",
        )

        # Verify result tuple shape
        assert len(result) == 5, f"Expected 5-tuple, got {len(result)}"
        model, clip, vae, checkpoint_name, info = result
        assert clip is None, f"clip should be None in diffusion mode, got {clip}"
        assert vae is None, f"vae should be None in diffusion mode, got {vae}"
        assert model is not None, "model should not be None"
        # checkpoint_name should be the relative name
        assert checkpoint_name == "krea2_unet_4.safetensors"
        # info should mention the category
        assert "diffusion_models" in info.lower()


def test_load_checkpoint_rotated_checkpoints_mode():
    """checkpoints mode: returns (model, clip, vae, name, info) like today."""
    from nodes.checkpoint_rotation import CheckpointRotationNode

    # Set up stubbed filename_lists for checkpoints
    from utils.model_discovery import filename_lists as _fl
    _fl["checkpoints"] = ["krea2Softrealism_v10.safetensors"]

    with mock.patch.object(CheckpointRotationNode, "IS_CHANGED", return_value=0.0):
        node = CheckpointRotationNode()

        result = node.load_checkpoint_rotated(
            subfolder="",
            change_interval=1,
            batch_index=0,
            rotation_mode="sequential",
            seed=42,
            checkpoint_filter="",
            model_folder="checkpoints",
        )

        assert len(result) == 5
        model, clip, vae, checkpoint_name, info = result
        assert clip is not None, "clip should not be None in checkpoints mode"
        assert vae is not None, "vae should not be None in checkpoints mode"
        assert checkpoint_name == "krea2Softrealism_v10.safetensors"


def test_empty_discovery_raises():
    """Empty discovery → raises ModelNotFoundError."""
    from nodes.checkpoint_rotation import CheckpointRotationNode

    from utils.model_discovery import filename_lists as _fnl
    _fnl["checkpoints"] = []

    with mock.patch.object(CheckpointRotationNode, "IS_CHANGED", return_value=0.0):
        node = CheckpointRotationNode()

        try:
            node.load_checkpoint_rotated(
                subfolder="",
                change_interval=1,
                batch_index=0,
                rotation_mode="sequential",
                seed=42,
                checkpoint_filter="",
                model_folder="checkpoints",
            )
            assert False, "Should have raised ModelNotFoundError"
        except ModelNotFoundError:
            pass  # Expected