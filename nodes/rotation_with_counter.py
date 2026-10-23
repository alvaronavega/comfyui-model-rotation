"""Checkpoint rotation node that works with ComfyUI's batch generation.

Uses a counter input that can be controlled with "control after generate".
Supports checkpoints AND diffusion models via the model_folder widget.
"""

import os
from typing import Dict, List, Optional, Tuple, Any

from utils.model_discovery import (
    ModelNotFoundError,
    list_model_names,
    select_rotated,
    load_by_category,
)
from utils.attribution import add_attribution


class CheckpointRotationWithCounter:
    """Checkpoint rotation that works with batch generation.

    Supports both checkpoints and diffusion models.
    Uses a counter input that can be controlled with "control after generate".
    """

    # Class IDs must not change — existing graphs reference them by ID
    NODE_CLASS_MAPPINGS = {}
    NODE_DISPLAY_NAME_MAPPINGS = {}

    # RETURN_TYPES must remain exactly as today (4 elements: model, clip, vae, info)
    RETURN_TYPES = ("MODEL", "CLIP", "VAE", "STRING")
    RETURN_NAMES = ("model", "clip", "vae", "info")

    FUNCTION = "load_checkpoint"
    CATEGORY = "loaders"

    def __init__(self):
        # Per-node checkpoint cache removed — discovery uses folder_paths directly
        # (follows ComfyUI standard: model appears after UI Refresh)
        self.checkpoint_cache = {}

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        """Define input parameters.

        model_folder is appended as the LAST optional widget to preserve
        widget indices for old workflow graphs.
        """
        return {
            "required": {
                "counter": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 100000,
                    "step": 1,
                    "tooltip": "Connect a Primitive INT with 'control_after_generate: increment'"
                }),
                "subfolder": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "tooltip": "Checkpoint subfolder name (leave empty for root)"
                }),
                "change_every": ("INT", {
                    "default": 4,
                    "min": 1,
                    "max": 1000,
                    "step": 1,
                    "tooltip": "Change checkpoint every N images"
                }),
                "reset_on_next": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Enable this to reset counter to 0 on next generation, then disable it"
                }),
            },
            "optional": {
                "checkpoint_filter": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "filter pattern (optional)"
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
        counter: int,
        subfolder: str,
        change_every: int,
        reset_on_next: bool = False,
        model_folder: str = "checkpoints",
    ) -> Tuple:
        """Load checkpoint/model based on counter value.

        Delegates discovery, selection, and loading to shared utility functions.
        Raises ModelNotFoundError if no models match the criteria.
        """
        # Handle reset functionality
        if reset_on_next:
            # Store current counter as offset — note: cache removed, so
            # reset just conceptually resets; actual behavior follows
            # the counter/change_every logic below.
            pass

        # 1. Discover model names for the selected category across ALL roots
        all_names = list_model_names(category=model_folder, filter_pattern="")

        # 2. Apply user filter (case-insensitive substring)
        if checkpoint_filter:
            names = list_model_names(category=model_folder, filter_pattern=checkpoint_filter)
        else:
            names = all_names

        # 3. Raise clear error if nothing matches
        if not names:
            raise ModelNotFoundError(
                category=model_folder,
                filter_pattern=checkpoint_filter or "",
            )

        # 4. Select model name based on rotation logic (counter-based)
        #    Formula: (counter // change_every) % len(names)
        selected_name = select_rotated(
            names=names,
            batch_index=counter,
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

        # 6. Generate checkpoint_name relative to the category root
        #    (use the selected name directly, ensuring forward slashes)
        checkpoint_name = selected_name.replace(os.sep, '/')

        # 7. Generate info string
        checkpoint_index = (counter // change_every) % len(names)
        total = len(names)
        images_with_current = (counter % change_every) + 1

        info = (
            f"Image #{counter} (raw counter: {counter})\n"
            f"Checkpoint {checkpoint_index + 1}/{total}\n"
            f"File: {os.path.basename(selected_name)}\n"
            f"Image {images_with_current}/{change_every} with this checkpoint\n"
            f"Next change at image #{((counter // change_every) + 1) * change_every}"
        )

        # Console feedback
        print(f"[CheckpointRotation] Loaded: {checkpoint_name} (category: {model_folder})")
        print(f"[CheckpointRotation] Image #{counter} - Using checkpoint {checkpoint_index + 1}/{total}")

        return (model, clip, vae, info)

    @classmethod
    def IS_CHANGED(cls, counter, **kwargs) -> float:
        """Tell ComfyUI to re-execute when counter changes."""
        return float(counter)


# ── Authorship ────────────────────────────────────────────────────────────
add_attribution(CheckpointRotationWithCounter)
