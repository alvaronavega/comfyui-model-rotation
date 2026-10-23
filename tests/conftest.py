"""
Test scaffolding module for comfyui-model-rotation.
Provides stub modules for folder_paths and comfy.sd to enable unit testing
without a running ComfyUI instance.
"""

import sys
import types
from typing import Any, Dict, List, Optional, Tuple


# ── fake folder_paths ──────────────────────────────────────────────────────
class STUBFolderPaths:
    """Stubs for ComfyUI's folder_paths module."""

    # Maps category -> list of filenames (relative names as returned by get_filename_list)
    filename_lists: Dict[str, List[str]] = {
        "checkpoints": [
            "krea2Softrealism_v10.safetensors",
            "krea2WRC8_3210425.safetensors",
            "krea2DreamShaper_v7.safetensors",
            "modelB.safetensors",
            "modelC.ckpt",
        ],
        "diffusion_models": [
            "krea2_unet_4.safetensors",
            "krea2_unet_5.safetensors",
        ],
        "unet": [
            "krea2_unet_4.safetensors",
            "krea2_unet_5.safetensors",
        ],
    }

    # Maps (category, relative_name) -> absolute path on disk (used by get_full_path)
    full_paths: Dict[Tuple[str, str], str] = {
        ("checkpoints", "krea2Softrealism_v10.safetensors"): (
            r"C:\AI\Projetos\comfyui-model-rotation\models\checkpoints\krea2Softrealism_v10.safetensors"
        ),
        ("checkpoints", "krea2WRC8_3210425.safetensors"): (
            r"C:\AI\Projetos\comfyui-model-rotation\models\checkpoints\krea2WRC8_3210425.safetensors"
        ),
        ("checkpoints", "krea2DreamShaper_v7.safetensors"): (
            r"C:\AI\Projetos\comfyui-model-rotation\models\checkpoints\krea2DreamShaper_v7.safetensors"
        ),
        ("diffusion_models", "krea2_unet_4.safetensors"): (
            r"C:\AI\Projetos\comfyui-model-rotation\models\diffusion_models\krea2_unet_4.safetensors"
        ),
        ("diffusion_models", "krea2_unet_5.safetensors"): (
            r"C:\AI\Projetos\comfyui-model-rotation\models\diffusion_models\krea2_unet_5.safetensors"
        ),
    }

    @staticmethod
    def get_filename_list(category: str) -> List[str]:
        """Return the list of filenames for the given category (all registered roots scanned)."""
        return list(STUBFolderPaths.filename_lists.get(category, []))

    @staticmethod
    def get_full_path(category: str, name: str) -> Optional[str]:
        """Return the absolute path for a given category + name, or None if not found."""
        return STUBFolderPaths.full_paths.get((category, name))

    @staticmethod
    def get_folder_paths(category: str) -> List[str]:
        """Return the list of registered folder paths for a category."""
        # Simplified: return a single representative path per category
        return [f"C:\\AI\\Projetos\\comfyui-model-rotation\\models\\{category}"]


# Attach to sys.modules so that `import folder_paths` inside node methods picks this up
sys.modules.setdefault("folder_paths", STUBFolderPaths())


# ── fake comfy / comfy.sd ──────────────────────────────────────────────────
import importlib.util

# Create a proper "comfy" package so that `import comfy.sd` works outside ComfyUI
_comfy_mod = types.ModuleType("comfy")
_comfy_mod.__path__ = []  # namespace package
_comfy_mod.__package__ = "comfy"
sys.modules["comfy"] = _comfy_mod

# Create the sd submodule and attach it
_sd_mod = types.ModuleType("comfy.sd")
_sd_mod.__package__ = "comfy.sd"
# Default return for load_checkpoint_guess_config: (model, clip, vae, clipvision)
_sd_mod.load_checkpoint_guess_config = staticmethod(
    lambda checkpoint_path,
    output_vae=True,
    output_clip=True,
    embedding_directory=None: ("stub_model", "stub_clip", "stub_vae", None)
)
# Default return for load_diffusion_model: (model,)
_sd_mod.load_diffusion_model = staticmethod(
    lambda checkpoint_path, model_options=None: ("stub_diffusion_model",)
)
sys.modules["comfy.sd"] = _sd_mod


# Ensure the stubbed folder_paths is the one we defined (re-assign after comfy import)
# This is a safety net in case node imports re-import folder_paths
sys.modules["folder_paths"] = STUBFolderPaths()


def reset_stubs() -> None:
    """Reset all stubs to their default state (useful between test modules)."""
    STUBFolderPaths.filename_lists = {
        "checkpoints": [],
        "diffusion_models": [],
        "unet": [],
    }
    STUBFolderPaths.full_paths = {}
    STDDSStub.guess_config_result = ("stub_model", "stub_clip", "stub_vae", None)
    STDDSStub.diffusion_result = ("stub_diffusion_model",)