"""
Test the workflow sanitizer: no local path may leak into the PNG metadata.

Verifies:
- our own path widgets (custom_path, manifest_path) are replaced by a label
- any other absolute Windows path found in the graph is scrubbed
- UNC paths are scrubbed
- relative paths and plain values are untouched
- the PNG really carries the sanitized graph
"""

import os
import sys
import types

import pytest

_fp = types.ModuleType("folder_paths")
_fp.get_full_path = lambda c, n: None
_fp.get_folder_paths = lambda c: []
sys.modules.setdefault("folder_paths", _fp)

from nodes.save_with_checkpoint import SaveImageWithCheckpoint  # noqa: E402


# ── Unit level ──────────────────────────────────────────────────────────────

def test_scrub_windows_path():
    """An absolute Windows path must be replaced."""
    text = r"salvando em C:\Users\alvar\Imagens\privado\arquivo.png"
    out = SaveImageWithCheckpoint._scrub_paths(text)
    assert "C:\\Users" not in out
    assert "<path>" in out


def test_scrub_unc_path():
    """A UNC path must be replaced."""
    text = r"\\servidor\compartilhado\pasta\arquivo"
    out = SaveImageWithCheckpoint._scrub_paths(text)
    assert "servidor" not in out
    assert "<path>" in out


def test_scrub_keeps_relative_and_plain():
    """Relative paths and plain text must survive untouched."""
    for text in ("modelos/krea2.safetensors", "uma frase normal", "C:o", ""):
        assert SaveImageWithCheckpoint._scrub_paths(text) == text


def test_sanitize_replaces_our_path_widgets():
    """custom_path and manifest_path must become neutral labels."""
    graph = {
        "8": {
            "class_type": "SaveImageWithCheckpoint",
            "inputs": {
                "custom_path": r"C:\AI\privado",
                "manifest_path": r"C:\AI\privado\manifest.json",
                "filename_prefix": "arte",
                "enable_metadata": True,
            },
        }
    }
    out = SaveImageWithCheckpoint._sanitize_workflow(graph)
    inputs = out["8"]["inputs"]
    assert inputs["custom_path"] == "<custom_path>"
    assert inputs["manifest_path"] == "<manifest_path>"
    assert inputs["filename_prefix"] == "arte"
    assert inputs["enable_metadata"] is True


def test_sanitize_walks_lists_and_nested():
    """Nested structures must be walked too."""
    graph = {"a": [{"b": (r"D:\data\x.png",)}, r"E:\out\y.png"], "c": {"d": r"F:\z"}}
    out = SaveImageWithCheckpoint._sanitize_workflow(graph)
    flat = repr(out)
    assert "D:\\data" not in flat
    assert "E:\\out" not in flat
    assert "F:\\z" not in flat


def test_sanitize_does_not_touch_numbers_or_booleans():
    """Non-string values must be preserved exactly."""
    graph = {"n": 42, "f": 4.5, "b": True, "none": None}
    assert SaveImageWithCheckpoint._sanitize_workflow(graph) == graph


# ── End to end: the PNG must not carry the local paths ─────────────────────

def test_png_metadata_has_no_local_path(tmp_path):
    """The real PNG must not contain any absolute path of this machine."""
    import json as _json
    import numpy as np
    from PIL import Image

    secret_path = r"C:\Users\alvar\Documents\MeuProjeto\Secreto"

    class _Cpu:
        def numpy(self):
            return np.zeros((4, 4, 3), dtype=np.float32)

    class _Img:
        shape = (4, 4, 3)

        def cpu(self):
            return _Cpu()

    prompt = {
        "8": {
            "class_type": "SaveImageWithCheckpoint",
            "inputs": {
                "custom_path": secret_path,
                "manifest_path": secret_path + r"\manifest.json",
            },
        },
        "9": {
            "class_type": "LoadImage",
            "inputs": {"image": r"D:\fotos\minha\imagem.png"},
        },
    }

    node = SaveImageWithCheckpoint()
    node.save_images(
        images=[_Img()],
        checkpoint_name="krea2.safetensors",
        filename_prefix="arte",
        prompt=prompt,
        extra_pnginfo={"workflow": {"nodes": [{"widgets_values": [secret_path]}]}},
        custom_path=str(tmp_path),
        embed_workflow=True,
        enable_metadata=True,
    )

    pngs = [f for f in os.listdir(tmp_path) if f.endswith(".png")]
    assert len(pngs) == 1
    with Image.open(os.path.join(tmp_path, pngs[0])) as img:
        info = img.info

    blob = " ".join(str(v) for v in info.values())
    assert "MeuProjeto" not in blob, f"the local path leaked into the PNG: {blob[:400]}"
    assert "minha" not in blob, f"another local path leaked: {blob[:400]}"
    assert "C:\\Users" not in blob
    assert "D:\\fotos" not in blob

    # The graph is still there, just sanitized
    graph = _json.loads(info["prompt"])
    assert graph["8"]["inputs"]["custom_path"] == "<custom_path>"
    assert "<path>" in graph["9"]["inputs"]["image"]
