"""
Test for model discovery: ModelNotFoundError + list_model_names.

Verifies:
- list_model_names returns sorted .safetensors/.ckpt/.pt/.pth names
- filter_pattern (case-insensitive substring) narrows the list
- empty result + filter → raises ModelNotFoundError with category+filter in message
- unfiltered empty list → raises ModelNotFoundError with category in message
"""

import pytest

from utils.model_discovery import list_model_names, ModelNotFoundError


# ── helpers ─────────────────────────────────────────────────────────────────
def make_stub_filename_lists(**categories):
    """Set the module-level filename_lists for list_model_names to use."""
    from utils import model_discovery as md
    md.filename_lists = categories


# ── tests ───────────────────────────────────────────────────────────────────

def test_list_model_names_basic():
    """Unfiltered list returns .safetensors/.ckpt/.pt/.pth files only, sorted."""
    make_stub_filename_lists(
        checkpoints=[
            "z_model.safetensors",
            "a_model.ckpt",
            "m_model.pt",
            "random.txt",
            "b_model.safetensors",
        ]
    )
    names = list_model_names("checkpoints")
    # Only supported extensions, sorted alphabetically
    expected = sorted(["a_model.ckpt", "b_model.safetensors", "m_model.pt", "z_model.safetensors"])
    assert names == expected, f"Expected {expected}, got {names}"


def test_list_model_names_with_filter():
    """Filter (case-insensitive substring) narrows the list to matches."""
    make_stub_filename_lists(
        checkpoints=[
            "krea2Softrealism_v10.safetensors",
            "krea2WRC8_3210425.safetensors",
            "krea2DreamShaper_v7.safetensors",
            "other_model.ckpt",
        ]
    )
    names = list_model_names("checkpoints", filter_pattern="soft")
    # Only those containing "soft" (case-insensitive) substring, sorted
    expected = sorted(["krea2Softrealism_v10.safetensors"])
    assert names == expected, f"Expected {expected}, got {names}"


def test_list_model_names_filter_no_match_raises():
    """Filter matching zero files raises ModelNotFoundError mentioning category+filter."""
    make_stub_filename_lists(
        checkpoints=[
            "model_a.safetensors",
            "model_b.ckpt",
        ]
    )
    with pytest.raises(ModelNotFoundError) as excinfo:
        list_model_names("checkpoints", filter_pattern="nonexistent")
    err = excinfo.value
    assert err.category == "checkpoints", f"Expected category 'checkpoints', got '{err.category}'"
    assert "nonexistent" in str(err), f"Error message should contain filter, got: {err}"
    # Message should also mention the category
    msg = str(err)
    assert "checkpoints" in msg


def test_list_model_names_empty_unfiltered_raises():
    """Empty list (no files at all) raises ModelNotFoundError with category in message."""
    make_stub_filename_lists(
        checkpoints=[]  # no files
    )
    with pytest.raises(ModelNotFoundError) as excinfo:
        list_model_names("checkpoints")
    err = excinfo.value
    assert err.category == "checkpoints"
    msg = str(err)
    assert "checkpoints" in msg


def test_list_model_names_diffusion_models():
    """list_model_names works with diffusion_models category too."""
    make_stub_filename_lists(
        diffusion_models=[
            "unet_4.safetensors",
            "unet_5.safetensors",
        ]
    )
    names = list_model_names("diffusion_models")
    expected = sorted(["unet_4.safetensors", "unet_5.safetensors"])
    assert names == expected, f"Expected {expected}, got {names}"