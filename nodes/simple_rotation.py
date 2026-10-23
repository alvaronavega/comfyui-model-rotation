"""Simplified checkpoint rotation node with built-in counter.

Supports both checkpoints and diffusion models via the model_folder widget.
Just set folder and interval - that's it.
"""

import os
from typing import Dict, List, Optional, Tuple, Any

from utils.model_discovery import (
    ModelNotFoundError,
    list_model_names,
    select_rotated,
    load_by_category,
)


class SimpleCheckpointRotation:
    """Simplified checkpoint rotation with built-in counter.

    Supports both checkpoints and diffusion models.
    Just set folder and interval - that's it.
    """

    # Class IDs must not change
    NODE_CLASS_MAPPINGS = {}
    NODE_DISPLAY_NAME_MAPPINGS = {}

    # RETURN_TYPES must remain exactly as today (4 elements)
    RETURN_TYPES = ("MODEL", "CLIP", "VAE", "STRING")
    RETURN_NAMES = ("model", "clip", "vae", "info")

    FUNCTION = "load_checkpoint"
    CATEGORY = "loaders"

    # Class-level counter (shared across all instances for simplicity)
    _counter = 0

    def __init__(self):
        # Cache removed — discovery uses folder_paths directly
        pass

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        """Define input parameters.

        model_folder is appended as the LAST optional widget.
        """
        return {
            "required": {
                "subfolder": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "tooltip": "Checkpoint subfolder (leave empty for all checkpoints)"
                }),
                "change_every": ("INT", {
                    "default": 4,
                    "min": 1,
                    "max": 1000,
                    "step": 1,
                    "tooltip": "Change checkpoint every N images"
                }),
                "auto_increment": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "Automatically increment counter (turn OFF for manual control)"
                }),
            },
            "optional": {
                "manual_index": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 100000,
                    "tooltip": "Manual index (only used if auto_increment is OFF)"
                }),
                # New widget: dropdown to pick model category (last optional widget)
                "model_folder": (["checkpoints", "diffusion_models", "unet"], {
                    "default": "checkpoints",
                    "placeholder": "model category"
                }),
            }
        }

    def load_checkpoint(
        self,
        subfolder: str,
        change_every: int,
        auto_increment: bool = True,
        manual_index: int = 0,
        model_folder: str = "checkpoints",
    ) -> Tuple:
        """Load checkpoint/model with rotation.

        Delegates discovery, selection, and loading to shared utility functions.
        Raises ModelNotFoundError if no models match the criteria.
        """
        # Determine current index
        if auto_increment:
            current_index = SimpleCheckpointRotation._counter
            SimpleCheckpointRotation._counter += 1
        else:
            current_index = manual_index

        # 1. Discover model names for the selected category across ALL roots
        all_names = list_model_names(category=model_folder, filter_pattern="")

        # 2. Apply user filter (case-insensitive substring)
        if hasattr(self, 'checkpoint_filter') and self.checkpoint_filter:
            # Note: checkpoint_filter not in signature for simplicity;
            # could add it later if needed
            names = list_model_names(category=model_folder, filter_pattern=self.checkpoint_filter)
        else:
            names = all_names

        # 3. Raise clear error if nothing matches
        if not names:
            raise ModelNotFoundError(
                category=model_folder,
                filter_pattern="",
            )

        # 4. Select model name based on rotation logic
        #    Formula: (current_index // change_every) % len(names)
        selected_name = select_rotated(
            names=names,
            batch_index=current_index,
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

        # 7. Generate info string
        checkpoint_index = (current_index // change_every) % len(names)
        total = len(names)
        info = (
            f"Image #{current_index}\n"
            f"Checkpoint {checkpoint_index + 1}/{total}\n"
            f"Changes every {change_every} images\n"
            f"Mode: {'Auto' if auto_increment else 'Manual'}"
        )

        # Console feedback
        print(f"[SimpleCheckpointRotation] Image #{current_index} - Using checkpoint {checkpoint_index + 1}/{total}: {selected_name}")

        return (model, clip, vae, info)

    @classmethod
    def reset_counter(cls):
        """Reset the counter to 0."""
        cls._counter = 0
        print("[SimpleCheckpointRotation] Counter reset to 0")

    @classmethod
    def IS_CHANGED(cls, **kwargs) -> float:
        """Force re-execution every time."""
        return float(cls._counter)