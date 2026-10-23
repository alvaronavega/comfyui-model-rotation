"""Alternative checkpoint rotation using direct checkpoint index control.

Supports both checkpoints and diffusion models via the model_folder widget.
Works more reliably with control_after_generate.
"""

import os
from typing import Dict, List, Optional, Tuple, Any

from utils.model_discovery import (
    ModelNotFoundError,
    list_model_names,
    select_rotated,
    load_by_category,
)


class CheckpointRotationSimple:
    """Simplified checkpoint rotation that takes a direct checkpoint index.

    Supports both checkpoints and diffusion models.
    For "change every N images", use increment step = 1 and this formula:
    actual_checkpoint = (index // N) % num_checkpoints
    """

    # Class IDs must not change
    NODE_CLASS_MAPPINGS = {}
    NODE_DISPLAY_NAME_MAPPINGS = {}

    # RETURN_TYPES: 5 elements (model, clip, vae, checkpoint_name, debug_info)
    # This node has a different RETURN_TYPE signature from the others,
    # so we keep it as-is — the model_folder widget is still added.
    RETURN_TYPES = ("MODEL", "CLIP", "VAE", "STRING", "STRING")
    RETURN_NAMES = ("model", "clip", "vae", "checkpoint_name", "debug_info")

    FUNCTION = "load_checkpoint"
    CATEGORY = "loaders"

    def __init__(self):
        # Per-node caches removed — discovery uses folder_paths directly
        self.checkpoint_cache = {}
        self.checkpoint_list_cache = {}

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        """Define input parameters.

        model_folder is appended as the LAST optional widget.
        """
        return {
            "required": {
                "checkpoint_index": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 100000,
                    "step": 1,
                    "tooltip": "Connect Primitive INT with control_after_generate: increment"
                }),
                "subfolder": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "tooltip": "Checkpoint subfolder (leave empty for root)"
                }),
                "change_every": ("INT", {
                    "default": 4,
                    "min": 1,
                    "max": 1000,
                    "step": 1,
                    "tooltip": "Change checkpoint every N images"
                }),
            },
            "optional": {
                # New widget: dropdown to pick model category (last optional widget)
                "model_folder": (["checkpoints", "diffusion_models", "unet"], {
                    "default": "checkpoints",
                    "placeholder": "model category"
                }),
            }
        }

    def load_checkpoint(
        self,
        checkpoint_index: int,
        subfolder: str,
        change_every: int,
        model_folder: str = "checkpoints",
    ) -> Tuple:
        """Load checkpoint based on index.

        Delegates discovery, selection, and loading to shared utility functions.
        Raises ModelNotFoundError if no models match the criteria.
        """
        # 1. Discover model names for the selected category across ALL roots
        all_names = list_model_names(category=model_folder, filter_pattern="")

        # 2. Apply user filter (case-insensitive substring)
        # (checkpoint_filter not in signature for this variant; could add later)
        names = all_names

        # 3. Raise clear error if nothing matches
        if not names:
            raise ModelNotFoundError(
                category=model_folder,
                filter_pattern="",
            )

        # 4. Select model name based on rotation logic
        #    Formula: (checkpoint_index // change_every) % len(names)
        selected_name = select_rotated(
            names=names,
            batch_index=checkpoint_index,
            interval=change_every,
            mode="sequential",
            seed=0,
        )

        # 5. Load the model using category-aware loader
        model, clip, vae = load_by_category(
            category=model_folder,
            name=selected_name,
            embeddings_dir=None,
        )

        # 6. Generate checkpoint_name (forward slashes)
        checkpoint_name = selected_name.replace(os.sep, '/')

        # 7. Generate debug info
        actual_index = (checkpoint_index // change_every) % len(names)
        total = len(names)
        images_in_cycle = (checkpoint_index % change_every) + 1

        debug_info = (
            f"RAW INDEX: {checkpoint_index}\n"
            f"CHANGE EVERY: {change_every}\n"
            f"ACTUAL CHECKPOINT INDEX: {actual_index}\n"
            f"TOTAL CHECKPOINTS: {total}\n"
            f"IMAGE IN CYCLE: {images_in_cycle}/{change_every}\n"
            f"FILE: {os.path.basename(selected_name)}\n"
            f"NODE EXECUTED: YES"
        )

        # Console feedback
        print(f"[CheckpointRotation] Loading: {checkpoint_name} (category: {model_folder})")
        print(f"[CheckpointRotation] Image #{checkpoint_index} -> Checkpoint {actual_index + 1}/{total} ({images_in_cycle}/{change_every})")

        return (model, clip, vae, checkpoint_name, debug_info)

    @classmethod
    def IS_CHANGED(cls, checkpoint_index, **kwargs) -> float:
        """Return a value that changes when input changes.

        Critical for ComfyUI to determine if node needs re-execution.
        """
        return float(checkpoint_index)