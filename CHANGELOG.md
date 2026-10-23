# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/lang/en/).

## Version 2.0.0 (2026-10-23)

### Added

- **`model_folder` dropdown** on all loader nodes (`checkpoints` | `diffusion_models` | `unet`)
  - Default: `checkpoints` — existing graphs unchanged
- **`select_models` field** — comma-separated list of models to rotate between, so you
  can compare only the 2 you care about out of many
  - Priority: `select_models` > `checkpoint_filter` > every discovered model
  - Names that do not exist in the category are reported in the console and skipped
- **Cross-root model discovery** via `folder_paths.get_filename_list(category)` —
  scans ALL registered ComfyUI folder roots (local + ComfyUI-Shared + extra paths),
  fixing the root cause of the "No checkpoints found" bug
- **Diffusion model support**: `diffusion_models`/`unet` categories return
  `(model, None, None)` — clip and vae are `None`; users provide separate
  `CLIPLoader` and `VAELoader` nodes in the workflow
- **Clear error handling**: `ModelNotFoundError` raises with category+filter message
  instead of silently returning `(None, None, None, "ERROR", ...)`
- **`Save Image (Metadata & Export)`** — the save node became fully configurable:
  - `enable_metadata` / `embed_workflow` — control what is embedded in the PNG
    (`embed_workflow` is the biggest leak: it stores the whole graph)
  - `enable_txt_file` / `enable_json_file` — sidecar exports next to the image
  - `custom_filename` — custom names with `${checkpoint} ${seed} ${cfg} ...` wildcards
  - `custom_path` — alternative output folder
  - `secure_mode` — generic file names + salted-hash sidecar contents
  - `manifest_path` — private `hash -> real value` map
- **Automatic generation-info extraction** — the node walks the workflow graph and
  extracts `seed`, `steps`, `cfg`, `sampler_name`, `scheduler`, `denoise`,
  `checkpoint`, `diffusion_model`, `clip`, `clip_type`, `vae`, `loras`,
  `lora_strengths`, `controlnets`, `positive_prompt`, `negative_prompt`, size/crop
- **`utils/secure_hash.py`** — salted SHA-256 hashing, manifest build/merge/save/load
  and sidecar resolution; the salt lives in `utils/secure_config.json` and is never
  written to the sidecars
- **`tools/resolve_sidecar.py`** — CLI to reverse an obfuscated sidecar
  (`single`, `folder`, `brute` against a candidate list, `info` for the salt fingerprint)
- **Multi-language support (i18n)** — `utils/i18n.py` with ptbr (default), en and zh;
  the choice is persisted in `utils/language_config.json` and falls back to ptbr
- **ASCII art banner + detailed loading messages** printed when the node loads
- **Metadata savers** resolve model names across categories:
  - `SaveImageWithCheckpoint` embeds correct model name in PNG metadata
  - `AddCheckpointToMetadata` passes through resolved model info
- **All 5 loader variants** updated with the new `model_folder` widget:
  - `Checkpoint Rotation (Batch)` ⭐ (advanced, main node)
  - `Simple Checkpoint Rotation`
  - `Checkpoint Rotation (Debug)`
  - `Checkpoint Rotation Simple` (direct index control)
  - `Checkpoint Rotation With Counter` (batch generation)
- **Test suite** — 62 pytest tests covering discovery, rotation, loading, the save
  node, the i18n system, the secure hashing and the example workflow consistency
- **Version bump** to `2.0.0`

### Changed

- **Node display name**: "Save Image (with Checkpoint Info)" → "Save Image (Metadata & Export)"
  (the class ID `SaveImageWithCheckpoint` did not change, so old graphs keep working)
- **Node RETURN_TYPES** preserved unchanged for all classes — existing graphs
  continue to bind without modification
- **NODE_CLASS_MAPPINGS** and **NODE_DISPLAY_NAME_MAPPINGS** keys unchanged
- **`checkpoint_filter`** behavior: still case-insensitive substring, now also
  works over diffusion_models/unet name lists
- **`IS_CHANGED`** logic: preserved per-node behavior
- **`checkpoint_cache`** removed from advanced node — discovery uses
  ComfyUI's `folder_paths` standard (model appears after UI Refresh)

### Deprecated

- Per-node `checkpoint_cache` dict in `CheckpointRotationNode` — will be removed
  in a future minor release; use the standard ComfyUI Refresh button instead

### Removed

- (none)

### Fixed

- **Root cause**: old node scanned only `folder_paths.get_folder_paths("checkpoints")[0]`,
  which was the local Krea2 folder (empty) → `clip=None` downstream error
- **Discovery now walks all roots**: local `models/`, `ComfyUI-Shared/`, and any
  extra paths from `instance-model-paths` config
- **`load_by_category`**: dispatches to `load_checkpoint_guess_config` for
  checkpoints, `load_diffusion_model` for diffusion/unet
- **`resolve_model_path_for_metadata`**: new helper for saver nodes
- **i18n structure**: the translation table is keyed by node then language, and the
  default language is ptbr instead of whatever was left in the config

### Version 1.0.0 (2025-11-05)

- Initial release
- Checkpoint rotation with multiple modes (sequential, random, shuffle)
- Batch index tracking (Batch Index Counter + Simple Counter)
- Subfolder and filter support
- Comprehensive documentation