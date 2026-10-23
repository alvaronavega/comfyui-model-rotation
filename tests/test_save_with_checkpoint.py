"""
Test for SaveImageWithCheckpoint: configurable metadata + sidecar exports.

Verifies:
- INPUT_TYPES exposes all the new toggles
- Info extraction pulls seed/steps/cfg/sampler/prompts from the workflow graph
- enable_metadata=False → no checkpoint text in the PNG
- embed_workflow=False → no prompt text in the PNG
- enable_txt_file / enable_json_file → sidecar files are written
- secure_mode → sidecar values are hashed, filename uses generic placeholders
- custom_filename with ${...} wildcards is expanded
"""

import os
import json
import tempfile

import pytest

from nodes.save_with_checkpoint import SaveImageWithCheckpoint


# ── Fake workflow graph (shape of a real ComfyUI prompt) ───────────────────
FAKE_PROMPT = {
    "1": {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {"ckpt_name": "some_checkpoint.safetensors"},
    },
    "2": {
        "class_type": "KSampler",
        "inputs": {
            "seed": 123456789,
            "control_after_generate": "increment",
            "steps": 28,
            "cfg": 4.5,
            "sampler_name": "dpmpp_2m",
            "scheduler": "karras",
            "denoise": 1.0,
        },
    },
    "3": {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": "a beautiful mountain landscape, masterpiece"},
    },
    "4": {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": "blurry, low quality, worst quality"},
    },
    "5": {
        "class_type": "VAELoader",
        "inputs": {"vae_name": "qwen_image_vae.safetensors"},
    },
    "6": {
        "class_type": "LoraLoader",
        "inputs": {"lora_name": "style_lora.safetensors", "strength_model": 0.8, "strength_clip": 0.8},
    },
}


def _fake_image():
    """Create a tiny fake IMAGE tensor (torch-like object with .shape/.cpu().numpy())."""
    import numpy as np

    class _Cpu:
        def numpy(self):
            return np.zeros((4, 4, 3), dtype=np.float32)

    class _Img:
        shape = (4, 4, 3)

        def cpu(self):
            return _Cpu()

    return [_Img()]


# ── INPUT_TYPES ────────────────────────────────────────────────────────────

def test_input_types_expose_all_toggles():
    """All the new optional toggles must be present."""
    it = SaveImageWithCheckpoint.INPUT_TYPES()
    optional = it["optional"]
    for key in (
        "enable_metadata",
        "embed_workflow",
        "enable_txt_file",
        "enable_json_file",
        "custom_filename",
        "custom_path",
        "secure_mode",
        "ph_checkpoint",
        "ph_batch",
        "ph_seed",
    ):
        assert key in optional, f"Missing optional input: {key}"

    # Required inputs unchanged
    required = it["required"]
    assert list(required.keys()) == ["images", "checkpoint_name", "filename_prefix"]


# ── Info extraction ────────────────────────────────────────────────────────

def test_extract_generation_info():
    """The walker must pull the useful fields out of the workflow graph."""
    info = SaveImageWithCheckpoint._extract_generation_info(FAKE_PROMPT, None)
    assert info["seed"] == 123456789
    assert info["steps"] == 28
    assert info["cfg"] == 4.5
    assert info["sampler_name"] == "dpmpp_2m"
    assert info["scheduler"] == "karras"
    assert info["denoise"] == 1.0
    assert info["vae"] == "qwen_image_vae.safetensors"
    assert info["loras"] == ["style_lora.safetensors"]
    assert "beautiful mountain" in info["positive_prompt"]
    assert "worst quality" in info["negative_prompt"]


def test_extract_generation_info_handles_none():
    """A None prompt must not crash the extractor."""
    info = SaveImageWithCheckpoint._extract_generation_info(None, None)
    assert info == {}


# ── Saving behaviour ───────────────────────────────────────────────────────

def _run_save(tmp_path, **kwargs):
    """Run the node against a temp folder and return (result, folder)."""
    node = SaveImageWithCheckpoint()
    params = dict(
        images=_fake_image(),
        checkpoint_name="krea2Softrealism_v10.safetensors",
        filename_prefix="teste",
        checkpoint_info="info extra",
        prompt=FAKE_PROMPT,
        extra_pnginfo={"workflow": {"nodes": []}},
        custom_path=str(tmp_path),
    )
    params.update(kwargs)
    result = node.save_images(**params)
    return result, tmp_path


def test_saves_png_with_metadata(tmp_path):
    """Default: PNG is written and carries the checkpoint text."""
    from PIL import Image

    result, folder = _run_save(tmp_path)
    files = os.listdir(folder)
    pngs = [f for f in files if f.endswith(".png")]
    assert len(pngs) == 1, f"Expected one PNG, got {files}"

    with Image.open(os.path.join(folder, pngs[0])) as img:
        text = img.info
    assert "checkpoint" in text, f"PNG metadata keys: {list(text.keys())}"
    assert text["checkpoint"] == "krea2Softrealism_v10.safetensors"
    assert "prompt" in text, "workflow graph should be embedded by default"


def test_disable_metadata_and_workflow(tmp_path):
    """enable_metadata=False and embed_workflow=False → PNG reveals nothing."""
    from PIL import Image

    result, folder = _run_save(tmp_path, enable_metadata=False, embed_workflow=False)
    pngs = [f for f in os.listdir(folder) if f.endswith(".png")]
    with Image.open(os.path.join(folder, pngs[0])) as img:
        text = img.info
    assert "checkpoint" not in text, f"checkpoint should be absent, got {list(text.keys())}"
    assert "prompt" not in text, f"prompt should be absent, got {list(text.keys())}"


def test_txt_sidecar_written(tmp_path):
    """enable_txt_file=True → a .txt file next to the image with the data."""
    result, folder = _run_save(tmp_path, enable_txt_file=True, enable_json_file=False)
    txts = [f for f in os.listdir(folder) if f.endswith(".txt")]
    assert len(txts) == 1, f"Expected one .txt, got {os.listdir(folder)}"

    with open(os.path.join(folder, txts[0]), encoding="utf-8") as fh:
        content = fh.read()
    assert "seed: 123456789" in content, content
    assert "sampler_name: dpmpp_2m" in content, content
    assert "krea2Softrealism_v10.safetensors" in content, content


def test_json_sidecar_written(tmp_path):
    """enable_json_file=True → a .json file next to the image with the data."""
    result, folder = _run_save(tmp_path, enable_txt_file=False, enable_json_file=True)
    jsons = [f for f in os.listdir(folder) if f.endswith(".json")]
    assert len(jsons) == 1, f"Expected one .json, got {os.listdir(folder)}"

    with open(os.path.join(folder, jsons[0]), encoding="utf-8") as fh:
        data = json.load(fh)
    assert data["seed"] == 123456789
    assert data["sampler_name"] == "dpmpp_2m"
    assert data["checkpoint_name"] == "krea2Softrealism_v10.safetensors"


def test_secure_mode_hashes_sidecar_and_uses_generic_names(tmp_path):
    """secure_mode=True → no real values leak into the sidecar or the file name."""
    result, folder = _run_save(
        tmp_path,
        enable_txt_file=True,
        secure_mode=True,
        ph_checkpoint="model",
        ph_batch="idx",
        ph_seed="sd",
    )
    files = os.listdir(folder)
    txts = [f for f in files if f.endswith(".txt")]
    assert len(txts) == 1

    with open(os.path.join(folder, txts[0]), encoding="utf-8") as fh:
        content = fh.read()
    # The real values must NOT appear
    assert "123456789" not in content, content
    assert "dpmpp_2m" not in content, content
    assert "krea2Softrealism_v10" not in content, content
    # But the structure survives
    assert "seed:" in content, content
    assert "sampler_name:" in content, content

    # The PNG must not carry the real checkpoint either
    from PIL import Image
    pngs = [f for f in files if f.endswith(".png")]
    with Image.open(os.path.join(folder, pngs[0])) as img:
        text = img.info
    assert text.get("checkpoint") == "model", f"PNG metadata: {text}"


def test_custom_filename_wildcards(tmp_path):
    """custom_filename with ${...} placeholders must be expanded."""
    result, folder = _run_save(
        tmp_path,
        custom_filename="obra_${checkpoint}_s${seed}_c${cfg}",
        enable_txt_file=False,
    )
    pngs = [f for f in os.listdir(folder) if f.endswith(".png")]
    assert len(pngs) == 1
    name = pngs[0]
    assert "krea2Softrealism_v10" in name, name
    assert "s123456789" in name, name
    assert "c4.5" in name, name


def test_custom_path_used(tmp_path):
    """custom_path must control where the files land."""
    target = tmp_path / "subfolder"
    result, folder = _run_save(target, enable_txt_file=False)
    assert target.exists(), "custom_path folder should be created"
    assert any(f.endswith(".png") for f in os.listdir(target))


def test_secure_mode_writes_manifest(tmp_path, monkeypatch):
    """secure_mode + manifest_path must produce a reversible manifest."""
    from utils import secure_hash

    # Use a throwaway salt so the test is isolated.
    # It lives in its own subfolder so it never mixes with the sidecars.
    private_dir = tmp_path / "privado"
    cfg = private_dir / "secure_config.json"
    monkeypatch.setattr(secure_hash, "CONFIG_PATH", str(cfg))
    monkeypatch.setattr(secure_hash, "_salt_cache", None)

    manifest_path = private_dir / "manifest.json"
    result, folder = _run_save(
        tmp_path,
        enable_txt_file=False,
        enable_json_file=True,
        secure_mode=True,
        manifest_path=str(manifest_path),
    )

    assert manifest_path.exists(), "manifest file should have been written"

    from utils.secure_hash import load_manifest, resolve_sidecar
    manifest = load_manifest(str(manifest_path))
    assert manifest, "manifest should not be empty"

    # The sidecar must be resolvable back to the real values
    json_name = [f for f in os.listdir(folder) if f.endswith(".json")][0]
    with open(os.path.join(folder, json_name), encoding="utf-8") as fh:
        sidecar = json.load(fh)

    assert "seed" in sidecar, f"sidecar should carry the seed, got {list(sidecar.keys())}"

    resolved = resolve_sidecar(sidecar, manifest)
    assert resolved["seed"] == "123456789", resolved
    assert resolved["sampler_name"] == "dpmpp_2m", resolved
    assert resolved["checkpoint_name"] == "krea2Softrealism_v10.safetensors", resolved


def test_manifest_path_optional(tmp_path):
    """Without manifest_path the node must not fail."""
    result, folder = _run_save(tmp_path, enable_txt_file=True, secure_mode=True)
    assert any(f.endswith(".txt") for f in os.listdir(folder))
