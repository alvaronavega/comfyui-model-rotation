"""Custom save image node with configurable metadata and sidecar export.

Supports model names from checkpoints, diffusion_models, and unet categories.

Features
--------
* ``enable_metadata``  – embed checkpoint/model info into the PNG metadata
* ``embed_workflow``   – embed the ComfyUI workflow graph (prompt + extra_pnginfo).
  This is the biggest information leak: turn it OFF to make the PNG reveal nothing.
* ``enable_txt_file``  – write a ``.txt`` sidecar with the extracted generation info
* ``enable_json_file`` – write a ``.json`` sidecar with the extracted generation info
* ``custom_filename``  – custom file name supporting ``${...}`` wildcards
* ``custom_path``      – alternative output folder
* ``use_secure_mode``  – obfuscate the sidecar contents and the file name

Sidecar files are written next to the image and share its base name.
"""

import os
import json
import re
import time
import hashlib
import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo
from typing import Any, Dict, List, Optional, Tuple

from utils.model_discovery import resolve_model_path_for_metadata
from utils.secure_hash import (
    build_manifest,
    hash_mapping,
    load_manifest,
    merge_manifest,
    save_manifest,
)


# ── Fields we try to extract from the ComfyUI workflow graph ────────────────
# (node type -> list of input names we care about)
_INTERESTING_NODES = {
    "KSampler": ["seed", "control_after_generate", "steps", "cfg", "sampler_name",
                 "scheduler", "denoise"],
    "KSamplerAdvanced": ["add_noise", "noise_seed", "control_after_generate", "steps",
                         "cfg", "sampler_name", "scheduler", "noise_uncond"],
    "KSampler (Efficient)": ["seed", "control_after_generate", "steps", "cfg", "sampler_name",
                             "scheduler", "denoise"],
    "SamplerCustomAdvanced": ["add_noise", "noise_seed", "control_after_generate"],
    "CLIPTextEncode": ["text"],
    "CLIPTextEncodeSDXL": ["text_g", "text_l"],
    "CheckpointLoaderSimple": ["ckpt_name"],
    "UNETLoader": ["unet_name"],
    "DiffusionModelLoader": ["model_name"],
    "CLIPLoader": ["clip_name", "type"],
    "VAELoader": ["vae_name"],
    "LoraLoader": ["lora_name", "strength_model", "strength_clip"],
    "LoraLoaderModelOnly": ["lora_name", "strength_model"],
    "ControlNetLoader": ["control_net_name"],
    "ImageScale": ["upscale_method", "width", "height", "crop"],
}


class SaveImageWithCheckpoint:
    """Saves images with configurable checkpoint metadata and sidecar exports."""

    def __init__(self):
        self.output_dir = self.get_output_directory()
        self.type = "output"
        self.prefix_append = ""
        self.compress_level = 4

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        """Define input parameters with full customization options."""
        return {
            "required": {
                "images": ("IMAGE",),
                "checkpoint_name": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "tooltip": "Nome do modelo conectado do node de rotacao"
                }),
                "filename_prefix": ("STRING", {
                    "default": "ComfyUI",
                    "multiline": False,
                    "tooltip": "Prefixo do arquivo (pode conter pastas, ex: 'projeto/arte')"
                }),
            },
            "optional": {
                "checkpoint_info": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "tooltip": "Informacoes adicionais para gravar"
                }),
                # === O que gravar no PNG ===
                "enable_metadata": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "Gravar informacoes do modelo no metadata do PNG"
                }),
                "embed_workflow": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "Gravar o grafo do workflow no PNG. "
                               "DESATIVE para o PNG nao revelar nada sobre a geracao"
                }),
                # === Arquivos sidecar ===
                "enable_txt_file": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "Gravar um arquivo .txt ao lado da imagem com os dados da geracao"
                }),
                "enable_json_file": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Gravar um arquivo .json ao lado da imagem com os dados da geracao"
                }),
                # === Nome e caminho ===
                "custom_filename": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "Ex: obra_${checkpoint}_${batch}  (vazio = nome automatico)",
                    "tooltip": "Nome customizado. Placeholders: ${checkpoint} ${batch} ${seed} "
                               "${steps} ${cfg} ${sampler} ${mode} ${index} ${timestamp}"
                }),
                "custom_path": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "Ex: C:/AI/Imagens/export  (vazio = pasta padrao do ComfyUI)",
                    "tooltip": "Pasta alternativa para gravar os arquivos"
                }),
                "secure_mode": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Modo seguro: nomes de arquivo genericos e conteudo do "
                               "sidecar ofuscado (hash com salt). Nao revela modelo, seed ou prompt"
                }),
                "manifest_path": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "Ex: C:/AI/privado/manifest.json  (vazio = nao gravar)",
                    "tooltip": "Arquivo privado que guarda o mapa hash -> valor real. "
                               "Sem ele voce nao consegue reverter o sidecar ofuscado"
                }),
                # === Nomes usados no modo seguro / placeholders ===
                "ph_checkpoint": ("STRING", {
                    "default": "checkpoint",
                    "multiline": False,
                    "tooltip": "Texto substituto para o nome do modelo"
                }),
                "ph_batch": ("STRING", {
                    "default": "batch",
                    "multiline": False,
                    "tooltip": "Texto substituto para o indice do lote"
                }),
                "ph_seed": ("STRING", {
                    "default": "seed",
                    "multiline": False,
                    "tooltip": "Texto substituto para a seed"
                }),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO"
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    CATEGORY = "image"

    # ── Information extraction ───────────────────────────────────────────────

    @staticmethod
    def _extract_generation_info(prompt: Optional[dict],
                                 extra_pnginfo: Optional[dict]) -> Dict[str, Any]:
        """Walk the ComfyUI workflow graph and pull out every useful field.

        Returns a flat dict with keys such as ``seed``, ``steps``, ``cfg``,
        ``sampler_name``, ``scheduler``, ``denoise``, ``model``, ``clip``,
        ``vae``, ``loras``, ``positive_prompt``, ``negative_prompt``, ...
        """
        info: Dict[str, Any] = {}

        if not isinstance(prompt, dict):
            return info

        # Positive / negative prompt text
        for node_id, node_data in prompt.items():
            if not isinstance(node_data, dict):
                continue
            node_type = node_data.get("class_type", "")
            inputs = node_data.get("inputs", {}) or {}
            if node_type in ("CLIPTextEncode", "CLIPTextEncodeSDXL", "CLIPTextEncodeSDXLRefiner"):
                text = inputs.get("text")
                if isinstance(text, str) and text:
                    # Heuristic: negative prompts usually mention quality words
                    lowered = text.lower()
                    negative_markers = ("blurry", "worst quality", "low quality", "deformed",
                                        "bad anatomy", "watermark", "jpeg artifacts", "ugly")
                    is_negative = any(marker in lowered for marker in negative_markers)
                    if is_negative:
                        info.setdefault("negative_prompt", text)
                    else:
                        info.setdefault("positive_prompt", text)

        # Node inputs of interest
        for node_id, node_data in prompt.items():
            if not isinstance(node_data, dict):
                continue
            node_type = node_data.get("class_type", "")
            inputs = node_data.get("inputs", {}) or {}

            wanted = _INTERESTING_NODES.get(node_type)
            if not wanted:
                continue

            for field in wanted:
                if field not in inputs:
                    continue
                value = inputs[field]
                if value is None or value == "":
                    continue

                if field in ("seed", "noise_seed"):
                    info.setdefault("seed", value)
                elif field == "control_after_generate":
                    continue  # noise, not information
                elif field == "text" or field.startswith("text"):
                    continue  # handled above
                elif field == "ckpt_name":
                    info.setdefault("checkpoint", value)
                elif field in ("unet_name", "model_name"):
                    info.setdefault("diffusion_model", value)
                elif field == "clip_name":
                    info.setdefault("clip", value)
                elif field == "type":
                    info.setdefault("clip_type", value)
                elif field == "vae_name":
                    info.setdefault("vae", value)
                elif field == "lora_name":
                    info.setdefault("loras", []).append(value)
                elif field in ("strength_model", "strength_clip"):
                    info.setdefault("lora_strengths", []).append(value)
                elif field == "control_net_name":
                    info.setdefault("controlnets", []).append(value)
                else:
                    info.setdefault(field, value)

        return info

    @staticmethod
    def _hash_value(value: Any, length: int = 12) -> str:
        """Hash *value* with the project salt (kept for backwards compatibility)."""
        from utils.secure_hash import hash_value
        return hash_value(value, length=length)

    # ── Filename helpers ────────────────────────────────────────────────────

    @staticmethod
    def _sanitize(value: str) -> str:
        """Remove characters that are illegal in file names."""
        return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(value)).strip()

    def _build_placeholders(self, checkpoint_name: str, gen_info: Dict[str, Any],
                            index: int, batch_index: Optional[int] = None) -> Dict[str, str]:
        """Build the mapping used to expand the ``${...}`` wildcards."""
        basename = os.path.basename(checkpoint_name) if checkpoint_name else ""
        model_stem = basename.rsplit(".", 1)[0] if basename else ""

        seed = gen_info.get("seed", "")
        steps = gen_info.get("steps", "")
        cfg = gen_info.get("cfg", "")
        sampler = gen_info.get("sampler_name", "")

        return {
            "checkpoint": self._sanitize(model_stem),
            "model": self._sanitize(model_stem),
            "batch": str(batch_index if batch_index is not None else index),
            "index": str(index),
            "seed": str(seed),
            "steps": str(steps),
            "cfg": str(cfg),
            "sampler": self._sanitize(sampler),
            "timestamp": str(int(gen_info.get("timestamp", 0))),
        }

    @classmethod
    def _expand(cls, template: str, placeholders: Dict[str, str]) -> str:
        """Replace every ``${key}`` occurrence in *template*."""
        result = template
        for key, value in placeholders.items():
            result = result.replace("${" + key + "}", value)
            result = result.replace("{" + key + "}", value)
        return result

    # ── Main entry point ────────────────────────────────────────────────────

    def save_images(
        self,
        images,
        checkpoint_name: str = "",
        filename_prefix: str = "ComfyUI",
        checkpoint_info: str = "",
        prompt=None,
        extra_pnginfo=None,
        enable_metadata: bool = True,
        embed_workflow: bool = True,
        enable_txt_file: bool = True,
        enable_json_file: bool = False,
        custom_filename: str = "",
        custom_path: str = "",
        secure_mode: bool = False,
        manifest_path: str = "",
        ph_checkpoint: str = "checkpoint",
        ph_batch: str = "batch",
        ph_seed: str = "seed",
    ):
        """Save images with configurable metadata and sidecar exports."""
        filename_prefix += self.prefix_append

        image_height = images[0].shape[0] if len(images) > 0 else 512
        image_width = images[0].shape[1] if len(images) > 0 else 512

        # Resolve output folder (custom path wins over ComfyUI default)
        if custom_path and custom_path.strip():
            save_dir = os.path.abspath(os.path.expanduser(custom_path.strip()))
            os.makedirs(save_dir, exist_ok=True)
        else:
            save_dir = self.get_output_directory()

        full_output_folder, filename, counter, subfolder, filename_prefix = \
            self.get_save_path(filename_prefix, save_dir, image_width, image_height)

        results: List[Dict[str, str]] = []

        # Resolve the model name across categories (checkpoints, diffusion_models, unet)
        resolved_path = resolve_model_path_for_metadata(checkpoint_name) if checkpoint_name else None
        resolved_model = os.path.basename(resolved_path) if resolved_path else checkpoint_name

        # Extract every useful piece of information from the workflow graph
        gen_info = self._extract_generation_info(prompt, extra_pnginfo)
        gen_info["timestamp"] = time.time()
        if checkpoint_name:
            gen_info.setdefault("checkpoint", checkpoint_name)
        if resolved_model:
            gen_info.setdefault("model", resolved_model)

        for (batch_number, image) in enumerate(images):
            i = 255. * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))

            metadata = PngInfo()

            # ── Workflow graph (biggest leak — toggleable) ──────────────────
            if embed_workflow:
                if prompt is not None:
                    metadata.add_text("prompt", json.dumps(prompt))
                if extra_pnginfo is not None:
                    for x in extra_pnginfo:
                        metadata.add_text(x, json.dumps(extra_pnginfo[x]))

            # ── Checkpoint / model info (toggleable) ────────────────────────
            if enable_metadata and checkpoint_name:
                if secure_mode:
                    metadata.add_text("checkpoint", ph_checkpoint)
                    metadata.add_text("model", ph_checkpoint)
                else:
                    metadata.add_text("checkpoint", checkpoint_name)
                    metadata.add_text("model", resolved_model or checkpoint_name)

            if checkpoint_info:
                metadata.add_text("checkpoint_info", checkpoint_info)

            # ── Build the file name ──────────────────────────────────────────
            placeholders = self._build_placeholders(checkpoint_name, gen_info, counter)
            if secure_mode:
                placeholders["checkpoint"] = self._sanitize(ph_checkpoint)
                placeholders["batch"] = self._sanitize(ph_batch)
                placeholders["seed"] = self._sanitize(ph_seed)

            if custom_filename and custom_filename.strip():
                stem = self._expand(custom_filename.strip(), placeholders)
                file = f"{self._sanitize(stem)}_{counter:05}_.png"
            else:
                file = f"{filename}_{counter:05}_.png"

            img.save(
                os.path.join(full_output_folder, file),
                pnginfo=metadata,
                compress_level=self.compress_level
            )

            # ── Sidecar files ───────────────────────────────────────────────
            base_name = file[:-4] if file.lower().endswith(".png") else os.path.splitext(file)[0]

            sidecar_payload: Dict[str, Any] = dict(gen_info)
            sidecar_payload["checkpoint_name"] = checkpoint_name
            sidecar_payload["resolved_model"] = resolved_model
            if checkpoint_info:
                sidecar_payload["checkpoint_info"] = checkpoint_info

            if secure_mode:
                # Hash with the project salt (stored in utils/secure_config.json,
                # never written to the sidecar).
                sidecar_payload = hash_mapping(sidecar_payload)
                # Build the reverse lookup so the owner can resolve hashes later.
                original_payload = dict(gen_info)
                original_payload["checkpoint_name"] = checkpoint_name
                original_payload["resolved_model"] = resolved_model
                if checkpoint_info:
                    original_payload["checkpoint_info"] = checkpoint_info
                new_entries = build_manifest(original_payload, sidecar_payload)
                if manifest_path and manifest_path.strip():
                    target = manifest_path.strip()
                    merged = merge_manifest(load_manifest(target), new_entries)
                    save_manifest(merged, target)

            if enable_txt_file:
                txt_path = os.path.join(full_output_folder, base_name + ".txt")
                try:
                    with open(txt_path, "w", encoding="utf-8") as fh:
                        for key, value in sidecar_payload.items():
                            fh.write(f"{key}: {value}\n")
                except OSError as exc:
                    print(f"[SaveImageWithCheckpoint] Could not write .txt sidecar: {exc}")

            if enable_json_file:
                json_path = os.path.join(full_output_folder, base_name + ".json")
                try:
                    with open(json_path, "w", encoding="utf-8") as fh:
                        json.dump(sidecar_payload, fh, ensure_ascii=False, indent=4)
                except OSError as exc:
                    print(f"[SaveImageWithCheckpoint] Could not write .json sidecar: {exc}")

            results.append({
                "filename": file,
                "subfolder": subfolder,
                "type": self.type
            })

            counter += 1

            print(f"[SaveImageWithCheckpoint] Saved {file} (checkpoint: {checkpoint_name}, "
                  f"txt: {enable_txt_file}, json: {enable_json_file}, secure: {secure_mode})")

        return {"ui": {"images": results}}

    def get_output_directory(self):
        """Get output directory from ComfyUI."""
        try:
            import folder_paths
            return folder_paths.get_output_directory()
        except Exception:
            return os.path.join(os.path.dirname(__file__), "..", "..", "output")

    def get_save_path(self, filename_prefix, output_dir, image_width=512, image_height=512):
        """Get save path details."""
        try:
            import folder_paths
            return folder_paths.get_save_image_path(
                filename_prefix,
                output_dir,
                image_width,
                image_height
            )
        except Exception:
            # Fallback (mirrors the ComfyUI implementation)
            def map_filename(filename):
                prefix_len = len(os.path.basename(filename_prefix))
                prefix = filename[:prefix_len + 1]
                try:
                    digits = int(filename[prefix_len + 1:].split('_')[0])
                except Exception:
                    digits = 0
                return (digits, prefix)

            def compute_vars(text, width, height):
                text = text.replace("%width%", str(width))
                text = text.replace("%height%", str(height))
                return text

            filename_prefix = compute_vars(filename_prefix, image_width, image_height)
            subfolder = os.path.dirname(os.path.normpath(filename_prefix))
            filename = os.path.basename(os.path.normpath(filename_prefix))
            full_output_folder = os.path.join(output_dir, subfolder)

            try:
                counter = max(
                    filter(
                        lambda a: a[1][:-1] == filename and a[1][-1] == "_",
                        map(map_filename, os.listdir(full_output_folder))
                    )
                )[0] + 1
            except ValueError:
                counter = 1
            except FileNotFoundError:
                os.makedirs(full_output_folder, exist_ok=True)
                counter = 1

            return full_output_folder, filename, counter, subfolder, filename_prefix

    @classmethod
    def IS_CHANGED(cls, images, checkpoint_name, **kwargs):
        """Force re-execution when the checkpoint name changes."""
        return checkpoint_name
