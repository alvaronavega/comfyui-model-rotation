# Multi-Model Rotation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every loader variant of comfyui-model-rotation accept checkpoints AND diffusion models (unet-style files with no embedded CLIP), scan all registered folder roots, and fail with a clear error instead of silently returning `clip=None`.

**Architecture:** New shared module `utils/model_discovery.py` owns model discovery (via ComfyUI's own `folder_paths.get_filename_list(category)` — covers ALL registered roots incl. ComfyUI-Shared), rotation selection, and category-aware loading. The four loader node files keep their class IDs, RETURN_TYPES and required inputs, but delegate discovery/loading to the shared module and gain one new optional widget `model_folder`. Metadata saver nodes resolve names across categories.

**Tech Stack:** Python 3.13 (ComfyUI venv), pytest, stdlib only. ComfyUI runtime imports (`folder_paths`, `comfy.sd`) are stubbed in tests.

**Spec:** Requirements agreed in conversation 2026-10-23 (root-cause investigated in the Krea2 instance — see Global Constraints below for the binding decisions):
1. Dropdown `model_folder` with choices `checkpoints | diffusion_models | unet`, default `checkpoints`, appended as the LAST optional widget (keeps old workflow graphs widget-aligned and behaving as today).
2. `diffusion_models`/`unet` category → load via `comfy.sd.load_diffusion_model(absolute_path)`, outputs `(model, None, None, name, info)`. User keeps their own `CLIPLoader` (text encoder, krea2 type) + `VAELoader` in the graph — as in the working Krea2 workflow.
3. Discovery uses `folder_paths.get_filename_list(category)` so ALL registered roots are visible (fixes "No checkpoints found" caused by only scanning `get_folder_paths("checkpoints")[0]`, which is the empty local folder).
4. No checkpoints found → raise `ModelNotFoundError` with category + filter in the message (red node card with real message) — replaces the silent `return (None, None, None, "ERROR", ...)` pattern that produced `clip input is invalid: None` downstream.
5. Remove the per-node `checkpoint_cache` dict; model list freshness now follows ComfyUI standard (`get_filename_list` + UI Refresh button), same as built-in loaders.
6. Node class IDs (`CheckpointRotation`, `CheckpointRotationSimple`, `SimpleCheckpointRotation`, `CheckpointRotationWithCounter`, `BatchIndexCounter`, `SimpleCounter`, `CheckpointFilename`, `SaveImageWithCheckpoint`) and `RETURN_TYPES`/`RETURN_NAMES` stay EXACTLY unchanged so existing graphs keep binding.

## Global Constraints

- Python 3.13 compatible; no new runtime dependencies; tests use pytest only.
- No GUI/API/behavior change for existing `checkpoints`-category graphs: default category `checkpoints`, default subfolder `""`, same outputs in the same order.
- Node class IDs and `NODE_DISPLAY_NAME_MAPPINGS` keys unchanged (graphs reference IDs, not display names).
- All probe/loading of files goes through `folder_paths.get_full_path(category, name)` (never build paths by string concatenation).
- Messages printed in English, prefixed with the node tag already used (`[CheckpointRotation]` style stays).
- Repo: `C:\AI\Projetos\comfyui-model-rotation`, branch `feat/support-diffusion-models` created off the current default branch before Task 1; commit after every task.
- Do NOT touch the Krea2 instance (`C:\AI\ComfyUI_Instances\Krea2\...`) in this plan; installation is a separate manual step after user review.

## Review Focus

Inputs/failure modes most likely to bite a person using this software:

1. `checkpoint_filter` that matches zero files in `diffusion_models` — user must see which category AND filter failed. → pinned by test `test_list_model_names_filter_no_match_raises` (Task 2).
2. Same model filename available in local root AND `ComfyUI-Shared` root — must resolve deterministically (first registered root wins via `get_full_path`) and never crash. → `test_load_by_category_same_name_two_roots` (Task 4).
3. Old workflow JSON without the new `model_folder` widget — must default to `checkpoints` and behave exactly like today (required-widget order untouched). → `test_optional_widget_order_preserved` (Task 6).
4. Diffusion model selected while user wrongly connects the node's `clip` output — discovery is fine but clip is `None`; the `info` output must warn in the string, and the message must name the category. → `test_diffusion_info_warns_no_clip` (Task 5).
5. Random/shuffle modes must be reproducible: same seed + same batch group → same model name, even though inputs are names (strings) instead of absolute paths. → `test_select_rotated_random_reproducible` (Task 3).

---

### Task 1: Test scaffolding with ComfyUI stubs

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/__init__.py` (empty, keeps pytest happy on Windows paths)
- Test: `tests/test_scaffolding.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: fixture `comfyui_stubs` that injects `sys.modules["folder_paths"]` and `sys.modules["comfy"]`, `sys.modules["comfy.sd"]` with mutable values `STUB.filename_lists: dict[str, list[str]]`, `STUB.full_paths: dict[tuple[str, str], str]`, and `STUB.guess_config_result` / `STUB.diffusion_result` that tests overwrite. Produces the convention "tests import node modules lazily AFTER installing stubs" used by all later tasks.

- [ ] **Step 1: Write the scaffolding test** asserting: with stubs installed, `import nodes.checkpoint_rotation` succeeds and `CheckpointRotationNode.RETURN_TYPES == ("MODEL", "CLIP", "VAE", "STRING", "STRING")`.
- [ ] **Step 2: Run** `python -m pytest tests/test_scaffolding.py -v` → FAIL (imports fail — no stubs exist yet).
- [ ] **Step 3: Implement `tests/conftest.py`** — autouse fixture installing the stub modules (simple `types.ModuleType` objects with the listed attributes + `load_checkpoint_guess_config` / `load_diffusion_model` functions raising `AssertionError("stub hit")` by default).
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `test: add ComfyUI stub scaffolding`.

### Task 2: `ModelNotFoundError` + `list_model_names`

**Files:**
- Create: `utils/model_discovery.py`
- Test: `tests/test_model_discovery.py`

**Interfaces:**
- Consumes: `folder_paths.get_filename_list(category) -> list[str]` (stubbed).
- Produces:
  - `class ModelNotFoundError(RuntimeError)` — attributes `category: str`, `filter_pattern: str`.
  - `list_model_names(category: str, filter_pattern: str = "") -> list[str]` — ComfyUI-style names (`"Krea2/model.safetensors"`), sorted; when the result is empty raises `ModelNotFoundError` whose message contains the category, the filter (when non-empty), and a hint to check the folder / hit Refresh.

- [ ] **Step 1: Write failing tests:** (a) stub lists `["b_hero.safetensors", "a/lower.safetensors", "notes.txt"]` → returns the two model names in sorted order (`.safetensors`, `.ckpt`, `.pt`, `.pth` only); (b) filter `"hero"` keeps only matches (case-insensitive substring); (c) filter `"nomatch"` → raises `ModelNotFoundError` and `.category == "diffusion_models"`; (d) unfiltered empty list → raises with category in message.
- [ ] **Step 2: Run** `python -m pytest tests/test_model_discovery.py -v` → FAIL.
- [ ] **Step 3: Implement** the module (reuse `SUPPORTED_EXTENSIONS` list; extension check via `os.path.splitext(name)[1].lower()`).
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: category-aware model discovery over all roots`.

### Task 3: `select_rotated` (name-based rotation)

**Files:**
- Modify: `utils/model_discovery.py` (append)
- Test: `tests/test_select_rotated.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `select_rotated(names: list[str], batch_index: int, interval: int, mode: str, seed: int) -> str | None` — returns `None` for an empty list; otherwise `(batch_index // interval) % len(names)` picks the slot; `sequential` = list order, `random` = `random.Random(seed + rotation_index).choice`, `shuffle` = `random.Random(seed).shuffle` then index. This is the port of `CheckpointUtils.select_checkpoint_from_list` (name list instead of absolute paths).

- [ ] **Step 1: Write failing tests:** deterministic sequential wrap-around (`interval=4`, indices 0..15 over 3 names); random reproducible (same seed twice → same pick, and documented different seed may differ); shuffle reproducible and every invocation hit the same permuted pattern; `select_rotated([], ...)` → `None`; unknown mode behaves as sequential.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** (single function; reuse the exact RNG recipe from `utils/checkpoint_utils.py` so behavior is unchanged).
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: name-based rotation selection`.

### Task 4: `load_by_category`

**Files:**
- Modify: `utils/model_discovery.py` (append)
- Test: `tests/test_load_by_category.py`

**Interfaces:**
- Consumes: Task 2's `ModelNotFoundError`; ComfyUI runtime `folder_paths.get_full_path(category, name) -> str | None`, `comfy.sd.load_checkpoint_guess_config(path, output_vae=True, output_clip=True, embedding_directory=folder_paths.get_folder_paths("embeddings"))`, `comfy.sd.load_diffusion_model(path)`.
- Produces: `DISCOVERY_CATEGORIES = ("checkpoints", "diffusion_models", "unet")` and `load_by_category(category: str, name: str, embeddings_dir: list[str]) -> tuple[model, clip, vae]` — resolves the absolute path with `get_full_path` (raises `ModelNotFoundError` naming category+name when absent on disk); `checkpoints` → first three items of `load_checkpoint_guess_config`; `diffusion_models`/`unet` → `load_diffusion_model(path)` and returns `(model, None, None)`.

- [ ] **Step 1: Write failing tests:** (a) checkpoints path returns stub trio `(M, C, V)`; (b) diffusion path calls `load_diffusion_model` exactly once with the resolved absolute path and returns `(M, None, None)`; (c) `unet` behaves as diffusion; (d) name missing from disk (get_full_path → None) raises with category+name in message; (e) REVIEW-FOCUS 2: stub with same name in two roots — call succeeds and gets SOME resolved path without raising.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** (branch on category string; no clever normalization).
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: category-aware model loading`.

### Task 5: Rewire `CheckpointRotationNode` (advanced loader)

**Files:**
- Modify: `nodes/checkpoint_rotation.py`
- Test: `tests/test_checkpoint_rotation_node.py`

**Interfaces:**
- Consumes: Tasks 2/3/4 functions.
- Produces: `CheckpointRotationNode.load_checkpoint_rotated(self, subfolder: str, change_interval: int, batch_index: int, rotation_mode: str, seed: int, checkpoint_filter: str = "", model_folder: str = "checkpoints")` returning `(model, clip, vae, checkpoint_name, info)`. Old per-node cache dict `self.checkpoint_cache` and the `_return_error` helper are GONE (imports of them removed); failure path is `raise ModelNotFoundError`. `subfolder` semantics: `model_folder` semantics: `subfolder` narrows names by prefix (`subfolder + "/"`), then filter applies.

- [ ] **Step 1: Write failing tests:** (a) diffusion mode returns `(model, None, None, name, info)` with name in ComfyUI form; (b) REVIEW-FOCUS 4: info string contains the category and the hint that diffusion models have no embedded CLIP (mention `CLIPLoader`); (c) empty discovery → raises `ModelNotFoundError`; (d) `checkpoints` mode end-to-end with stubs returns the trio like today; (e) subfolder `"sdxl"` only sees names under that prefix.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement:** replace body of `load_checkpoint_rotated` with calls to the three shared functions; keep the existing `[CheckpointRotation] Loaded: <name>` print. Delete `_discover_checkpoints`, `_load_checkpoint`, `_return_error`, `self.checkpoint_cache`, `self.last_checkpoint_path`, `__init__` customizations if unused. `IS_CHANGED` stays as-is.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: advanced loader supports diffusion models`.

### Task 6: Rewire the three remaining loaders + widget order pin

**Files:**
- Modify: `nodes/rotation_with_counter.py`, `nodes/simple_rotation.py`, `nodes/simple_rotation_direct.py`
- Test: `tests/test_loader_variants.py`

**Interfaces:**
- Consumes: shared functions + the Task-5 pattern.
- Produces: every loader's `INPUT_TYPES` optional dict ends with `"model_folder": (list(DISCOVERY_CATEGORIES), {"default": "checkpoints"})` — appended AFTER `checkpoint_filter` in the same dicts, and each node's execute now takes the `model_folder` kwarg (default `"checkpoints"`) and delegates exactly like Task 5. `CheckpointRotationWithCounter` is the ⭐ main node; check its internal counter wiring is untouched.

- [ ] **Step 1: Write failing test for REVIEW-FOCUS 3 (widget order):** for each of the 4 loader classes, `INPUT_TYPES()` required keys are exactly `["subfolder", "change_interval", "batch_index", "rotation_mode", "seed"]` in order, and optional keys end with `[..., "checkpoint_filter", "model_folder"]`. Plus one behavior spot-test per variant (diffusion mode → clip `None`).
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** the same body rewire in each file (mechanical; duplicates exist, do NOT restructure the files beyond the rewire).
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: all loader variants accept diffusion models`.

### Task 7: Metadata savers resolve across categories

**Files:**
- Modify: `nodes/save_with_checkpoint.py`, `nodes/add_checkpoint_metadata.py`, `nodes/checkpoint_filename.py` (if it resolves paths)
- Test: `tests/test_save_metadata_resolution.py`

**Interfaces:**
- Consumes: `DISCOVERY_CATEGORIES`.
- Produces: shared helper `resolve_model_path_for_metadata(name: str) -> str | None` in `utils/model_discovery.py` — tries `folder_paths.get_full_path(cat, name)` for each category in order and returns the first hit (or None). Savers use it instead of their current checkpoints-only / diffusion-then-checkpoints lookups. Output metadata string stays formatted as today.

- [ ] **Step 1: Write failing tests:** name only existing under `diffusion_models` resolves; name existing in BOTH categories resolves to the checkpoints hit first; unknown name → None (no raise, savers must not crash a finished image).
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** helper + replace the lookup sites in each saver file.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: metadata savers resolve diffusion model names`.

### Task 8: Branding, README, import smoke

**Files:**
- Modify: `__init__.py` (success/failure print block only + `__version__ = "2.0.0"`), `README.md` (intro, features, node reference gains `model_folder` widget, new "diffusion models" section explaining the CLIPLoader+VAELoader requirement with the krea2 example), `CHANGELOG.md` (new v2.0.0 entry)
- Test: `tests/test_init_registration.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `NODE_CLASS_MAPPINGS` unchanged (asserted by test), new version string.

- **Step 1: Write failing test:** import `__init__` with stubs; assert the 8 class IDs from Global Constraints exist in `NODE_CLASS_MAPPINGS` and `__version__ == "2.0.0"`.
- **Step 2: Run** → FAIL.
- **Step 3: Implement** branding edits (docs may exceed one step; keep each file edit separate and self-evident).
- **Step 4: Run** → PASS.
- **Step 5: Commit** `docs+chore: rebrand as comfyui-model-rotation, v2.0.0`.

### Task 9: Full verification gate (no code)

- [ ] **Step 1:** `python -m pytest tests -v` → all green.
- [ ] **Step 2:** `git log --oneline` shows one commit per task; clean `git status`.
- [ ] **Step 3:** Hand branch to user: summarize diff, push `feat/support-diffusion-models` to the fork (requires user's GitHub auth; ask before pushing), and present the manual install checklist for the Krea2 instance (copy folder into `custom_nodes`, rename original to `comfyui-change-checkpoint-randomly.disabled`, restart ComfyUI, load a Krea2 workflow with `Checkpoint Rotation (Batch)` + `CLIPLoader` + `VAELoader`, run 2 rotations). Installation happens only after the user approves.
