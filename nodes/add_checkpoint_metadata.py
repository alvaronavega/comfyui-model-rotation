"""Node that modifies workflow metadata to include checkpoint information.

Supports model names from checkpoints, diffusion_models, and unet categories.
This should work with any standard SaveImage node.
"""

import nodes
from typing import Dict, Tuple, Any

from utils.model_discovery import resolve_model_path_for_metadata
from utils.attribution import add_attribution


class AddCheckpointToMetadata:
    """Adds checkpoint information to the workflow metadata that SaveImage will use.

    This node passes through the images unchanged but modifies the metadata
    that will be saved by downstream SaveImage nodes.
    Now supports diffusion model names resolved across categories.
    """

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        """Define input parameters."""
        return {
            "required": {
                "images": ("IMAGE",),
                "checkpoint_name": ("STRING", {
                    "default": "",
                    "multiline": False,
                }),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)

    FUNCTION = "add_checkpoint_metadata"

    CATEGORY = "image"

    OUTPUT_NODE = False

    def add_checkpoint_metadata(
        self,
        images,
        checkpoint_name: str,
        prompt=None,
        extra_pnginfo=None
    ):
        """Add checkpoint to metadata and pass through images.

        Resolves the model name across categories (checkpoints, diffusion_models, unet)
        before embedding it in the prompt metadata.
        """

        # Resolve the model name across categories
        resolved_path = resolve_model_path_for_metadata(checkpoint_name) if checkpoint_name else None

        # Modify the prompt to include checkpoint info
        if prompt is not None:
            # Find our node in the prompt
            if isinstance(prompt, dict):
                for node_id, node_data in prompt.items():
                    if isinstance(node_data, dict) and node_data.get("class_type") == "AddCheckpointToMetadata":
                        # Add checkpoint as a visible input so it appears in metadata
                        if "inputs" not in node_data:
                            node_data["inputs"] = {}
                        # Use the original checkpoint_name as the primary field,
                        # but also store the resolved path info
                        node_data["inputs"]["checkpoint_used"] = checkpoint_name
                        # If we have a resolved path, add it as additional info
                        if resolved_path is not None:
                            node_data["inputs"]["model_resolved"] = os.path.basename(resolved_path)
                        print(f"[AddCheckpointToMetadata] Added checkpoint to metadata: {checkpoint_name}")
                        break

        # Pass through images unchanged
        return (images,)

    @classmethod
    def IS_CHANGED(cls, images, checkpoint_name, **kwargs):
        """Force re-execution when checkpoint changes."""
        return checkpoint_name


# ── Authorship ────────────────────────────────────────────────────────────
add_attribution(AddCheckpointToMetadata)
