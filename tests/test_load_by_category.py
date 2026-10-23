"""
Test for load_by_category: category-aware model loading (logic-flow tests).

Verifies:
- Name not in filename_lists → raises ModelNotFoundError
- Name in filename_lists for checkpoints → returns (model, clip, vae) placeholder tuple
- Name in filename_lists for diffusion_models → returns (model, None, None) placeholder tuple
- Name in filename_lists for unet → same as diffusion_models
"""

import pytest

from utils.model_discovery import load_by_category, ModelNotFoundError


# ── helper to reset module state between tests ──────────────────────────────
def _reset_md():
    import utils.model_discovery as md
    md.filename_lists = {}


# ── tests ───────────────────────────────────────────────────────────────────

def test_load_by_category_checkpoints_name_missing_raises():
    """Name not in filename_lists → ModelNotFoundError."""
    _reset_md()
    from utils.model_discovery import filename_lists as _fl
    _fl["checkpoints"] = []
    try:
        load_by_category("checkpoints", "nonexistent.safetensors", [])
        assert False, "Should have raised ModelNotFoundError"
    except ModelNotFoundError as e:
        assert e.category == "checkpoints"
        assert "nonexistent" in str(e)


def test_load_by_category_checkpoints_name_present():
    """Name present in filename_lists → returns placeholder tuple (3 elements)."""
    _reset_md()
    from utils.model_discovery import filename_lists as _fl
    _fl["checkpoints"] = ["krea2Softrealism_v10.safetensors"]
    model, clip, vae = load_by_category("checkpoints", "krea2Softrealism_v10.safetensors", [])
    assert isinstance(model, str)
    assert isinstance(clip, str)
    assert isinstance(vae, str)
    assert model == "stub_model"
    assert clip == "stub_clip"
    assert vae == "stub_vae"


def test_load_by_category_diffusion_name_present():
    """diffusion_models name present → returns (model, None, None) placeholder tuple."""
    _reset_md()
    from utils.model_discovery import filename_lists as _fl
    _fl["diffusion_models"] = ["krea2_unet_4.safetensors"]
    model, clip, vae = load_by_category("diffusion_models", "krea2_unet_4.safetensors", [])
    assert isinstance(model, str)
    assert clip is None
    assert vae is None


def test_load_by_category_unet_name_present():
    """unet name present → same as diffusion_models."""
    _reset_md()
    from utils.model_discovery import filename_lists as _fl
    _fl["unet"] = ["krea2_unet_5.safetensors"]
    model, clip, vae = load_by_category("unet", "krea2_unet_5.safetensors", [])
    assert isinstance(model, str)
    assert clip is None
    assert vae is None


def test_load_by_category_invalid_category():
    """Unknown category → raises ModelNotFoundError (name not found check)."""
    _reset_md()
    from utils.model_discovery import filename_lists as _fl
    _fl["checkpoints"] = []
    try:
        load_by_category("invalid_category", "any_name.safetensors", [])
        assert False, "Should have raised ModelNotFoundError"
    except ModelNotFoundError as e:
        assert e.category == "invalid_category"