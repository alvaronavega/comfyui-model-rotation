"""Main checkpoint rotation node for ComfyUI.

Supports rotating through checkpoints OR diffusion models (UNETs without embedded CLIP).
Uses ComfyUI's folder_paths to discover models across all registered roots
(including ComfyUI-Shared), and raises clear errors instead of silently returning None.

NODE CLASS ID: CheckpointRotation  — MUST NOT CHANGE for existing graphs.
RETURN_TYPES: ("MODEL", "CLIP", "VAE", "STRING", "STRING")  — UNCHANGED.
"""

import os
from typing import Dict, List, Optional, Tuple, Any

from utils.model_discovery import (
    ModelNotFoundError,
    list_model_names,
    select_rotated,
    load_by_category,
)
from utils.i18n import get, set_language, current_language, list_languages


class CheckpointRotationNode:
    """Rotate through checkpoints or diffusion models during batch generation."""

    # Class IDs must not change — existing graphs reference them by ID
    NODE_CLASS_MAPPINGS = {}
    NODE_DISPLAY_NAME_MAPPINGS = {}

    # RETURN_TYPES and RETURN_NAMES must remain exactly as today
    RETURN_TYPES = ("MODEL", "CLIP", "VAE", "STRING", "STRING")
    RETURN_NAMES = ("model", "clip", "vae", "checkpoint_name", "info")

    FUNCTION = "load_checkpoint_rotated"
    CATEGORY = "loaders"

    def __init__(self):
        # Per-node checkpoint cache removed — discovery uses folder_paths directly
        pass

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        """Define input parameters.

        model_folder is appended as the LAST optional widget to preserve
        old graph indices. Uses i18n translations for labels.
        """
        # Busca traduções para os labels
        model_folder_label = get("model_folder_label", "checkpoint_rotation")
        checkpoint_filter_label = get("checkpoint_filter_label", "checkpoint_rotation")
        info_title = get("info_title", "checkpoint_rotation")

        # Help text for the model_folder dropdown
        model_folder_help = get("model_folder_tooltip", "checkpoint_rotation")

        return {
            "required": {
                "subfolder": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": get("subfolder_placeholder", "checkpoint_rotation", ""),
                    "tooltip": get("subfolder_tooltip", "checkpoint_rotation",
                                   "Path to model subfolder relative to the category root")
                }),
                "change_interval": ("INT", {
                    "default": 1, "min": 1, "max": 10000, "step": 1,
                    "display": "number",
                    "tooltip": get("change_interval_tooltip", "checkpoint_rotation",
                                   "Number of images before switching model")
                }),
                "batch_index": ("INT", {
                    "default": 0, "min": 0, "max": 1000000, "step": 1,
                    "display": "number",
                    "tooltip": get("batch_index_tooltip", "checkpoint_rotation",
                                   "Current batch index (use BatchIndexCounter)")
                }),
                "rotation_mode": (["sequential", "random", "shuffle"], {
                    "default": "sequential",
                    "tooltip": get("rotation_mode_tooltip", "checkpoint_rotation",
                                   "How to select next model")
                }),
                "seed": ("INT", {
                    "default": 0,
                    "min": 0, "max": 0xffffffffffffffff,
                    "tooltip": get("seed_tooltip", "checkpoint_rotation",
                                   "Seed for random/shuffle modes")
                }),
            },
            "optional": {
                "checkpoint_filter": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": get("checkpoint_filter_placeholder", "checkpoint_rotation",
                                       "Case-insensitive substring match"),
                    "tooltip": get("checkpoint_filter_tooltip", "checkpoint_rotation",
                                   "Optional filter pattern (case-insensitive substring)")
                }),
                # New widget: dropdown to pick model category
                "model_folder": (["checkpoints", "diffusion_models", "unet"], {
                    "default": "checkpoints",
                    "placeholder": model_folder_label,
                    "tooltip": model_folder_help,
                }),
                # New field: explicit model selection (comma-separated names)
                # When provided, overrides the automatic discovery and rotates only
                # the models listed. Useful for comparing specific models side-by-side.
                "select_models": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": get("select_models_placeholder", "checkpoint_rotation",
                                       "Nomes separados por virgula (ex: a.safetensors, b.safetensors)"),
                    "tooltip": get("select_models_tooltip", "checkpoint_rotation",
                                   "Selecione modelos especificos para girar entre eles. "
                                   "Exemplo: 'krea2Softrealism_v10, krea2WRC8_3210425'")
                }),
            }
        }

    def load_checkpoint_rotated(
        self,
        subfolder: str,
        change_interval: int,
        batch_index: int,
        rotation_mode: str,
        seed: int,
        checkpoint_filter: str = "",
        model_folder: str = "checkpoints",
        select_models: str = "",
    ) -> Tuple:
        """Execute checkpoint/model rotation.

        Delegates discovery, selection, and loading to shared utility functions.
        Raises ModelNotFoundError if no models match (produces red node card with message).

        Priority when picking the candidate list:
            select_models (explicit names) > checkpoint_filter (substring) > everything
        """
        try:
            # 1. Discover model names for the selected category across ALL roots
            all_names = list_model_names(category=model_folder, filter_pattern="")

            # 2. Determine the candidate list
            #    Priority: explicit select_models > checkpoint_filter > all discovered
            if select_models and select_models.strip():
                # User typed an explicit list of model names (comma separated).
                # Keep only the ones that actually exist for this category.
                explicit_names = [
                    n.strip() for n in select_models.split(",") if n.strip()
                ]
                names = [n for n in explicit_names if n in all_names]
                missing = [n for n in explicit_names if n not in all_names]
                if missing:
                    print(
                        "[CheckpointRotation] WARNING: these names were not found in "
                        f"'{model_folder}' and were skipped: {', '.join(missing)}"
                    )
                if not names:
                    raise ModelNotFoundError(
                        category=model_folder,
                        filter_pattern=select_models,
                    )
            elif checkpoint_filter:
                names = list_model_names(
                    category=model_folder, filter_pattern=checkpoint_filter
                )
            else:
                names = all_names

            # 3. Raise clear error if nothing matches
            if not names:
                raise ModelNotFoundError(
                    category=model_folder,
                    filter_pattern=checkpoint_filter or "",
                )

            # 4. Select model name based on rotation logic
            selected_name = select_rotated(
                names=names,
                batch_index=batch_index,
                interval=change_interval,
                mode=rotation_mode,
                seed=seed,
            )

            # 5. Load the model using category-aware loader
            model, clip, vae = load_by_category(
                category=model_folder,
                name=selected_name,
                embeddings_dir=None,
            )

            # 6. Build checkpoint_name (relative path with forward slashes)
            #    This name is used by Image Saver Metadata and other nodes.
            #    We already validated the name exists via list_model_names above.
            checkpoint_name = selected_name.replace(os.sep, '/')

            # 7. Generate info string
            rotation_num = batch_index // change_interval
            try:
                idx = names.index(selected_name)
            except ValueError:
                idx = 0
            total = len(names)

            info = (
                f"Model: {selected_name}\n"
                f"Category: {model_folder}\n"
                f"Index: {idx + 1}/{total}\n"
                f"Batch: {batch_index}\n"
                f"Rotation: {rotation_num}\n"
                f"Mode: {rotation_mode}"
            )

            # Console feedback (preserves existing [CheckpointRotation] format)
            print(f"[CheckpointRotation] Loaded: {checkpoint_name} (category: {model_folder})")
            print(f"[CheckpointRotation] Output checkpoint_name for metadata: '{checkpoint_name}'")

            return (model, clip, vae, checkpoint_name, info)

        except ModelNotFoundError:
            raise
        except Exception as e:
            # Re-raise as RuntimeError to show a red node card with the error message
            raise RuntimeError(f"Error in checkpoint rotation: {e}") from None

    def IS_CHANGED(cls, **kwargs) -> float:
        """Re-execute when batch_index changes — preserves existing behavior."""
        return float(kwargs.get('batch_index', 0))