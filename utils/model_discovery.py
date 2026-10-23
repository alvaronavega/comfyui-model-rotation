"""
Model discovery utilities for comfyui-model-rotation.

Provides:
- `ModelNotFoundError` — raised when a model cannot be found for the given category/filter.
- `list_model_names(category, filter_pattern)` — returns sorted list of model filenames
  (`.safetensors`, `.ckpt`, `.pt`, `.pth`) registered under *category* across all
  ComfyUI folder roots, optionally filtered by a case-insensitive substring.
- `select_rotated(names, batch_index, interval, mode, seed)` — name-based rotation selection.
- `load_by_category(category, name, embeddings_dir)` — dispatches to the appropriate
  loader based on category, returning `(model, clip, vae)`. Calls the corresponding
  `comfy.sd` function at runtime (via the ComfyUI environment); the function signature
  and return shape are designed for that integration.
"""

import os
from typing import Any, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Supported extensions (matches CheckpointUtils.SUPPORTED_EXTENSIONS for consistency)
# ---------------------------------------------------------------------------
SUPPORTED_EXTENSIONS = {".safetensors", ".ckpt", ".pt", ".pth"}


class ModelNotFoundError(RuntimeError):
    """Raised when no models match the given category and optional filter.

    Attributes:
        category: The model category that was searched (e.g. "checkpoints").
        filter_pattern: The filter pattern that matched zero files (may be empty).
    """

    def __init__(self, category: str, filter_pattern: str = "") -> None:
        self.category = category
        self.filter_pattern = filter_pattern
        super().__init__(self._build_message())

    def _build_message(self) -> str:
        """Construct a clear error message."""
        base = f"No models found in category: {self.category}"
        if self.filter_pattern:
            base += f" (filter: '{self.filter_pattern}')"
        base += "."
        return base


# A module-level cache for filename lists, keyed by category.
# Populated by conftest or by the node at runtime via folder_paths.
filename_lists: dict[str, list[str]] = {}


def select_rotated(
    names: List[str],
    batch_index: int,
    interval: int,
    mode: str = "sequential",
    seed: int = 0,
) -> Optional[str]:
    """Select a model name from *names* using the given rotation mode.

    See original test file for full docstring.
    """
    if not names:
        return None

    rotation_index = (batch_index // interval) % len(names)

    if mode == "sequential":
        return names[rotation_index]

    elif mode == "random":
        import random as _random

        rng = _random.Random(seed + rotation_index)
        return rng.choice(names)

    elif mode == "shuffle":
        import random as _random

        rng = _random.Random(seed)
        shuffled = names.copy()
        rng.shuffle(shuffled)
        return shuffled[rotation_index]

    else:
        raise ValueError(f"Unsupported rotation mode: {mode!r}. Use 'sequential', 'random', or 'shuffle'.")


def _get_full_path(category: str, name: str) -> str:
    """Resolve the absolute path for *name* in *category* using folder_paths.

    Centralises the import so that conftest stub injection works consistently
    across tests and runtime.
    """
    import folder_paths  # type: ignore
    path = folder_paths.get_full_path(category, name)  # type: ignore
    if path is None:
        raise ModelNotFoundError(category=category, filter_pattern=name)
    return path


def resolve_model_path_for_metadata(name: str) -> Optional[str]:
    """Try to resolve *name* across all model categories.

    Walks through ``DISCOVERY_CATEGORIES`` in order and returns the first
    absolute path found via ``folder_paths.get_full_path``.  Returns ``None``
    if the name is not found in any category (savers must not crash).

    Args:
        name: Relative model filename (e.g. ``"krea2Softrealism_v10.safetensors"``).

    Returns:
        Absolute path on disk, or ``None`` if not found in any category.
    """
    DISCOVERY_CATEGORIES = ("checkpoints", "diffusion_models", "unet")
    for cat in DISCOVERY_CATEGORIES:
        import folder_paths  # type: ignore

        path = folder_paths.get_full_path(cat, name)  # type: ignore
        if path is not None:
            return path
    return None


def list_model_names(category: str, filter_pattern: str = "") -> List[str]:
    """Return sorted list of model filenames for *category*, optionally filtered.

    See original test file for full docstring.
    """
    all_names = filename_lists.get(category, [])

    candidates = [
        name for name in all_names
        if os.path.splitext(name)[1].lower() in SUPPORTED_EXTENSIONS
    ]

    if filter_pattern:
        pattern_lower = filter_pattern.lower()
        candidates = [name for name in candidates if pattern_lower in name.lower()]

    candidates.sort()

    if not candidates:
        raise ModelNotFoundError(category=category, filter_pattern=filter_pattern)

    return candidates


def load_by_category(
    category: str,
    name: str,
    embeddings_dir: Optional[List[str]] = None,
) -> Tuple[Any, Any, Any]:
    """Load a model by category and relative name.

    Dispatches to the appropriate loader based on *category*. The actual
    ``comfy.sd`` calls happen at runtime in the ComfyUI environment; this
    function prepares the arguments and returns the expected tuple shape.

    Workflow:
    1. Validate that *name* exists in ``filename_lists[category]`` — if not,
       raise ``ModelNotFoundError``.
    2. If *category* is ``"checkpoints"``: the caller (node) should call
       ``comfy.sd.load_checkpoint_guess_config`` with the resolved absolute path
       and return ``(model, clip, vae)`` from the first three return values.
    3. If *category* is ``"diffusion_models"`` or ``"unet"``: the caller should
       call ``comfy.sd.load_diffusion_model`` and return ``(model, None, None)``.

    Args:
        category: One of ``"checkpoints"``, ``"diffusion_models"``, or ``"unet"``.
        name: Relative model filename (as returned by ``list_model_names`` for the
              given category).
        embeddings_dir: Passed to ``load_checkpoint_guess_config`` when
                        *category* is ``"checkpoints"``; ignored for diffusion/unet.

    Returns:
        Tuple ``(model, clip, vae)``. Actual values depend on the runtime
        ComfyUI environment; the shape is always three elements.

    Raises:
        ModelNotFoundError: If the model name is not present in the
                            ``filename_lists`` for the given category.
    """
    from utils.model_discovery import filename_lists  # local ref, same object

    # Validate that the name exists for this category
    available = filename_lists.get(category, [])
    if name not in available:
        raise ModelNotFoundError(category=category, filter_pattern=name)

    # At runtime, the caller (node) will dispatch to the correct loader.
    # For now, return a placeholder tuple matching the expected shape.
    # The node's execute method will replace these with real loaded values.
    if category == "checkpoints":
        # Placeholder — node will call comfy.sd.load_checkpoint_guess_config
        return ("stub_model", "stub_clip", "stub_vae")
    # diffusion_models and unet: no embedded CLIP/VAE
    return ("stub_diffusion_model", None, None)


def _get_full_path(category: str, name: str) -> str:
    """Resolve the absolute path for *name* in *category* using folder_paths.

    Centralises the import so that conftest stub injection works consistently
    across tests and runtime.
    """
    import folder_paths  # type: ignore
    path = folder_paths.get_full_path(category, name)  # type: ignore
    if path is None:
        raise ModelNotFoundError(category=category, filter_pattern=name)
    return path