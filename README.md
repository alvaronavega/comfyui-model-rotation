# ComfyUI Checkpoint Rotation Node

A custom node for ComfyUI that enables automatic rotation through **checkpoints** or **diffusion models** (UNETs without embedded CLIP) during batch generation.

**Current version: 2.0.0** — supports checkpoints AND diffusion models across all registered ComfyUI folder roots.

## Features

- **Automatic Checkpoint/Diffusion Model Rotation**: Switch between models every N images
- **Category Dropdown** (`model_folder`): Choose from `checkpoints`, `diffusion_models`, or `unet`
- **Explicit Model Selection** (`select_models`): Rotate only between the 2 (or N) models you name
- **Subfolder Selection**: Pick models from specific subfolders within the chosen category
- **Multiple Rotation Modes**:
  - **Sequential**: Cycle through models in order
  - **Random**: Randomly select models (with seed for reproducibility)
  - **Shuffle**: Randomize order once, then cycle through
- **Model Filtering**: Filter models by name pattern (case-insensitive substring)
- **Batch Index Tracking**: Helper nodes to track generation progress
- **Cross-Root Discovery**: Scans ALL registered ComfyUI folder roots (local + ComfyUI-Shared), not just the first one
- **Clear Error Messages**: Raised as red node cards instead of silently returning `clip=None`
- **Configurable Metadata & Export** (`Save Image (Metadata & Export)`):
  - Toggle PNG metadata, workflow graph, `.txt` and `.json` sidecars independently
  - Automatic extraction of seed, steps, cfg, sampler, prompts, LoRAs, VAE, CLIP…
  - Custom file names with `${checkpoint}` `${seed}` `${cfg}` wildcards
  - Alternative output folder
  - **Secure mode**: salted-hash sidecars with a private manifest for later reversal
- **Multi-language (i18n)**: Português (ptbr, default), English, 中文 — persisted in the config
- **ASCII art banner** with detailed loading messages in the ComfyUI console

## Installation

### Method 1: Git Clone (Recommended)

1. Navigate to your ComfyUI custom nodes directory:
   ```bash
   cd ComfyUI/custom_nodes/
   ```

2. Clone this repository:
   ```bash
   git clone https://github.com/alvaronavega/comfyui-model-rotation.git
   ```

3. Restart ComfyUI

### Method 2: Manual Installation

1. Download this repository as ZIP
2. Extract to `ComfyUI/custom_nodes/comfyui-model-rotation/`
3. Restart ComfyUI

### Verify Installation

After restarting ComfyUI, you should see these new nodes in the node menu (under **loaders**):

- `Checkpoint Rotation (Batch)` — main rotation node
- `Save Image (with Checkpoint Info)` — use this for correct metadata
- `Checkpoint to Filename` — add checkpoint to filename
- `Checkpoint Rotation (Debug)` — debug mode
- `Simple Checkpoint Rotation` — simplified rotation
- `Batch Index Counter` — counter helper
- `Simple Counter` — basic counter

Look for the success message in the console:
```
[ComfyUI] Checkpoint Rotation Node loaded successfully!
```

## Node Reference

### 1. Checkpoint Rotation (Batch) ⭐

The main node that rotates through checkpoints or diffusion models.

**Location**: Add Nodes → loaders → Checkpoint Rotation (Batch)

**Inputs**:

- **subfolder** (STRING): Path to model subfolder relative to the category root
  - Leave empty `""` to use root of the selected category
  - Example: `"sdxl"`, `"sdxl/anime"`, `"realistic"`
- **change_interval** (INT): Number of images before switching model
  - Default: `1`
  - Example: `4` means switch model every 4 images
- **batch_index** (INT): Current position in batch generation
  - Connect to `Batch Index Counter` node for automatic tracking
  - Manual: increment this value in your workflow
- **rotation_mode** (COMBO): How to select the next model
  - `sequential`: Cycle through in order
  - `random`: Random selection (seed-based)
  - `shuffle`: Shuffle list once, then cycle
- **seed** (INT): Random seed for `random` and `shuffle` modes
  - Same seed = same model sequence
  - Different seed = different sequence
- **checkpoint_filter** (STRING, optional): Filter models by name pattern
  - Example: `"anime"` only loads models with "anime" in filename
  - Case-insensitive substring match
- **model_folder** (COMBO, optional): **New** — category of models to rotate
  - `checkpoints`: Standard ComfyUI checklists (has embedded CLIP/VAE)
  - `diffusion_models`: UNET-style models without embedded CLIP (requires separate CLIPLoader)
  - `unet`: Same as diffusion_models (alternative category name)
  - Default: `checkpoints`
- **select_models** (STRING, optional): **New** — explicit list of models to rotate between
  - Comma separated: `"krea2Softrealism_v10, krea2WRC8_3210425"`
  - Use this when you want to compare **only** 2 specific models out of many
  - Names that do not exist in the chosen category are reported in the console and skipped
  - Priority: `select_models` > `checkpoint_filter` > every discovered model

**Outputs**:

- **model**: Loaded model (connect to KSampler)
- **clip**: CLIP model (connect to CLIP Text Encode) — **`None`** when `model_folder` is `diffusion_models` or `unet`
- **vae**: VAE model (connect to VAE Decode) — **`None`** when `model_folder` is `diffusion_models` or `unet`
- **checkpoint_name**: Name of current model (relative path, for display/logging/metadata)
- **info**: Detailed information about current rotation state

> **Important**: When using `model_folder: diffusion_models` or `unet`, do NOT connect the node's `clip` output to CLIP Text Encode. Instead, use a separate `CLIPLoader` node (type `krea2` or your model's type) to provide the text encoder. The node's `vae` output is also `None` in these categories — use a separate `VAELoader` node.

### 2. Save Image (Metadata & Export) ⭐

Saves images with configurable metadata and sidecar (`.txt` / `.json`) exports.

**Location**: Add Nodes → image → Save Image (Metadata & Export)

Supports model names from `checkpoints`, `diffusion_models` and `unet` categories. The node resolves the model name across all categories to find the file on disk.

**Required inputs**:

- **images** (IMAGE): Input images to save
- **checkpoint_name** (STRING): Model name from the rotation node
- **filename_prefix** (STRING): Prefix for saved files (may contain subfolders)

**Optional inputs**:

| Option | Default | What it does |
|--------|---------|--------------|
| **checkpoint_info** | `""` | Extra text embedded in the PNG metadata |
| **enable_metadata** | `true` | Writes `checkpoint` + `model` text fields into the PNG |
| **embed_workflow** | `true` | Writes the whole workflow graph (`prompt` + `extra_pnginfo`) into the PNG — **this is the biggest information leak, turn it off to make the PNG reveal nothing** |
| **enable_txt_file** | `true` | Writes a `.txt` sidecar next to the image with the extracted data |
| **enable_json_file** | `false` | Writes a `.json` sidecar next to the image with the extracted data |
| **custom_filename** | `""` | Custom file name with `${...}` wildcards (see below) |
| **custom_path** | `""` | Alternative output folder (created if missing) |
| **secure_mode** | `false` | Generic file names + salted-hash sidecar contents |
| **manifest_path** | `""` | Private file storing the `hash -> real value` map (required to reverse a secure sidecar) |
| **ph_checkpoint** / **ph_batch** / **ph_seed** | `checkpoint` / `batch` / `seed` | Placeholder texts used by the secure mode |

**Outputs**: None (saves to disk)

#### What gets extracted automatically

The node walks the ComfyUI workflow graph and pulls out everything useful:

`seed`, `steps`, `cfg`, `sampler_name`, `scheduler`, `denoise`, `checkpoint`,
`diffusion_model`, `clip`, `clip_type`, `vae`, `loras`, `lora_strengths`,
`controlnets`, `positive_prompt`, `negative_prompt`, `width`, `height`, `crop`.

#### Filename wildcards

`custom_filename` accepts these placeholders:

```
${checkpoint}  ${model}  ${batch}  ${index}  ${seed}  ${steps}  ${cfg}  ${sampler}  ${timestamp}
```

Example: `obra_${checkpoint}_s${seed}_c${cfg}` →
`obra_krea2Softrealism_v10_s123456789_c4.5`

#### Sidecar files

The sidecar shares the image base name:

```
demo_00001_.png     <- the image
demo_00001_.txt     <- the sidecar (text format)
demo_00001_.json    <- the sidecar (json format)
```

#### Secure mode (privacy)

`secure_mode: true` replaces every sidecar value with a **salted SHA-256 hash** while
keeping the keys intact, so a validator can still compare and group images without
learning the real values.

```
seed: 15e2b0d3c338        <- hashed
steps: 59e19706d51d       <- hashed
```

To be able to read the values back later, set **manifest_path** to a private location.
The manifest maps every hash back to its real value, and the tool
`tools/resolve_sidecar.py` resolves a sidecar against it:

```bash
python tools/resolve_sidecar.py single  MINHA_IMAGEM.json  MEU_MANIFEST.json
python tools/resolve_sidecar.py folder PASTA_DE_IMAGENS    MEU_MANIFEST.json
python tools/resolve_sidecar.py brute  HASH_AQUI          lista_de_modelos.txt
python tools/resolve_sidecar.py info                      # mostra o "fingerprint" do salt
```

The salt itself lives in `utils/secure_config.json` (auto-generated on first use) and
is **never** written to the sidecars.

#### Privacy cheat sheet

| Goal | Settings |
|------|----------|
| Share everything | all `true` |
| Hide the prompt/seed but keep the model name | `embed_workflow: false` |
| Share a PNG that reveals nothing | `enable_metadata: false` + `embed_workflow: false` |
| Keep a private audit trail | the above + `enable_txt_file: true` + `secure_mode: true` + `manifest_path` |

#### Local paths never leak into the PNG

The embedded workflow graph stores the **widget values of every node**, and some
of them are local folders — our own `custom_path` / `manifest_path`, and any other
node that takes a path. Before writing the graph into the PNG the node
**sanitizes** it:

* the value of the known path widgets is replaced by a label (`<custom_path>`)
* any remaining absolute path (`C:\...` or `\\server\share`) becomes `<path>`

So the PNG never publishes the layout of the machine that produced it. Model
*filenames* are kept on purpose (they are relative, and they are what the
metadata is for).

#### What is private, and where it lives

| File | Secret? | Where it is | In git? |
|------|---------|-------------|---------|
| `utils/secure_config.json` (the **salt**) | semi | inside the node, `utils/` | **no** (git-ignored) |
| your **manifest.json** | **yes — this is the key** | wherever you point `manifest_path` | **no** (outside the repo) |
| `utils/language_config.json` | no | inside the node, `utils/` | no (git-ignored) |
| the sidecars | free to share | next to the images | no |

The salt is generated automatically on first use and the language preference falls
back to ptbr, so a fresh clone behaves correctly without them.

**Back up the manifest** — losing it makes the sidecars permanently unreadable
(that is the point) and losing the salt means the hashes can no longer be
recomputed either.

Public, committed examples live in [`examples/secure_mode/`](examples/secure_mode/):
they show the obfuscated sidecar, the manifest, the salt used and how to reverse
them. They contain fake data only.

### 3. Checkpoint to Filename

Creates a filename that includes model/checkpoint information.

**Location**: Add Nodes → utils → Checkpoint to Filename

**Inputs**:

- **checkpoint_name** (STRING): Model name from the rotation node
- **prefix** (STRING): Prefix for filename (default: "ComfyUI")
- **include_path** (BOOLEAN): Include subfolder path in filename

**Outputs**:

- **filename_prefix**: Filename prefix to connect to SaveImage

### 4. Checkpoint Rotation (Debug)

Debug mode that shows detailed rotation information.

**Location**: Add Nodes → loaders → Checkpoint Rotation (Debug)

Same inputs as the main rotation node, but with debug output.

### 5. Simple Checkpoint Rotation

Simplified rotation with built-in counter.

**Location**: Add Nodes → loaders → Simple Checkpoint Rotation

**Inputs**:

- **subfolder** (STRING): Checkpoint subfolder
- **change_every** (INT): Change checkpoint every N images
- **auto_increment** (BOOLEAN): Automatically increment counter
- **manual_index** (INT): Manual index (if auto_increment is OFF)

### 6. Batch Index Counter

Helper node to automatically track and increment batch index.

**Location**: Add Nodes → utils → Batch Index Counter

**Inputs**:

- **action** (COMBO): What to do with the counter
  - `increment`: Add to counter
  - `set`: Set to specific value
  - `reset`: Reset to 0
- **counter_id** (STRING, optional): Unique identifier for this counter
  - Default: `"default"`
  - Use different IDs for multiple independent counters
- **set_value** (INT): Value to set when action is "set"
- **increment_by** (INT): Amount to increment (default: 1)

**Outputs**:

- **batch_index**: Current counter value (connect to rotation node)
- **info**: Information string about counter state

### 7. Simple Counter

Basic counter that outputs sequential numbers.

**Location**: Add Nodes → utils → Simple Counter

**Inputs**:

- **start** (INT): Starting value (default: 0)
- **step** (INT): Increment amount (default: 1)

**Outputs**:

- **value**: Current counter value

## Usage Examples

### Example 1: Basic Rotation with Checkpoints

Generate 20 images, changing checkpoint every 4 images:

```
[Batch Index Counter]
  action: increment
  increment_by: 1
  └─→ batch_index

[Checkpoint Rotation (Batch)]
  subfolder: ""                    ← root checkpoints folder
  change_interval: 4
  batch_index: (from counter)
  rotation_mode: sequential
  └─→ model, clip, vae

[CLIP Text Encode (Positive)]
  clip: (from rotation loader)
  text: "your prompt"

[CLIP Text Encode (Negative)]
  clip: (from rotation loader)
  text: "negative prompt"

[KSampler]
  model: (from rotation loader)
  batch_size: 1  ← Important: use 1 for rotation
  └─→ latent

[VAE Decode]
  vae: (from rotation loader)
  samples: (from sampler)
  └─→ image

[Save Image (with Checkpoint Info)]
  images: (from decoder)
  checkpoint_name: (from rotation loader)
```

**Result**: 5 different checkpoints used (changing every 4 images: 4, 8, 12, 16, 20)

### Example 2: Random Rotation with Seed Control

Same setup as Example 1, but with random checkpoint selection:

```
[Checkpoint Rotation (Batch)]
  subfolder: "realistic"
  change_interval: 5
  rotation_mode: random
  seed: 12345  ← Controls which checkpoints are selected
```

**Result**: Different seed values produce different model sequences, but the same seed always produces the same sequence.

### Example 3: Using model_folder with Checkpoints

```
[Checkpoint Rotation (Batch)]
  model_folder: checkpoints          ← explicit (default)
  subfolder: "my_checkpoints"
  change_interval: 2
  rotation_mode: sequential
```

### Example 4: Using model_folder with Diffusion Models

This is the key new use case — rotate through diffusion-style UNET models that have **no embedded CLIP**. Your workflow must include separate CLIPLoader and VAELoader nodes:

```
[Checkpoint Rotation (Batch)]
  model_folder: diffusion_models     ← rotate diffusion models
  subfolder: ""                      ← root diffusion_models folder
  change_interval: 4
  rotation_mode: sequential
  seed: 42

[CLIPLoader]                         ← separate! type krea2 or your model
  models: (load your CLIP model here)
  └─→ clip

[VAELoader]                          ← separate!
  models: (load your VAE model here)
  └─→ vae

[KSampler]
  model: (from rotation loader)
  batch_size: 1
  └─→ latent

[VAE Decode]
  vae: (from VAELoader)              ← from separate loader
  samples: (from sampler)
  └─→ image

[Save Image (with Checkpoint Info)]
  images: (from decoder)
  checkpoint_name: (from rotation loader)
```

**Result**: Rotate through diffusion models while using separate CLIP and VAE — exactly the configuration that works on the Krea2 instance.

**Why this works**: Diffusion-style models (UNETs with fp8/int8 precision, no embedded CLIP) cannot provide CLIP text encoding. The `model_folder: diffusion_models` category makes the rotation node return `clip=None` and `vae=None`, and the info string warns the user to provide these via separate loaders. This matches the working Krea2 workflow where `CLIPLoader (type krea2)` and `VAELoader` are used alongside the rotation node.

### Example 5: Multiple Independent Counters

Use different counters for different purposes:

```
[Batch Index Counter A]
  counter_id: "main"
  action: increment
  └─→ for main model rotation

[Batch Index Counter B]
  counter_id: "secondary"
  action: increment
  increment_by: 2
  └─→ for different rotation speed
```

### Example 6: Filtering Models by Name

Load only specific model types:

```
[Checkpoint Rotation (Batch)]
  model_folder: checkpoints
  checkpoint_filter: "anime"  ← Only loads checkpoints with "anime" in name
  change_interval: 2
  rotation_mode: sequential
```

## Workflow Setup Guide

### Step-by-Step: Creating a Rotation Workflow

1. **Add Batch Index Counter**:
   - Right-click → Add Node → utils → Batch Index Counter
   - Set `action` to "increment"

2. **Add Checkpoint Rotation (Batch) Node**:
   - Right-click → Add Node → loaders → Checkpoint Rotation (Batch)
   - Connect `batch_index` output from counter to `batch_index` input
   - Set `subfolder` to your model folder (or leave empty for root)
   - Set `change_interval` to desired number (e.g., 4 for every 4 images)
   - Choose `rotation_mode` (sequential recommended for first try)
   - Set `model_folder` to the appropriate category:
     - `checkpoints` for standard checklists
     - `diffusion_models` for UNETs without embedded CLIP
     - `unet` as alternative to diffusion_models

3. **Connect to Your Workflow**:
   - Connect `model` output to KSampler
   - Connect `clip` output to CLIP Text Encode nodes
     - **If `model_folder` is `diffusion_models` or `unet`**: use a separate `CLIPLoader` node instead
   - Connect `vae` output to VAE Decode
     - **If `model_folder` is `diffusion_models` or `unet`**: use a separate `VAELoader` node instead

4. **Set Up Loop** (Important!):
   - Use ComfyUI's loop nodes or queue multiple prompts
   - Set KSampler `batch_size: 1` (critical for rotation)
   - Loop for total number of images you want

5. **Run Workflow**:
   - Execute the workflow
   - Checkpoint will automatically rotate based on your settings
   - Watch console for rotation messages

### Step-by-Step: Diffusion Model Workflow

1. Add the rotation node with `model_folder: diffusion_models`
2. Add a `CLIPLoader` node (type matching your model, e.g., `krea2`)
3. Add a `VAELoader` node (load your VAE model)
4. Connect outputs as in the KSampler setup
5. The rotation node will return `clip=None` and `vae=None` — the separate loaders provide these

## Troubleshooting

### No Models Found in Category

**Problem**: Error message "No models found in category: [name] (filter: '...')"

**Solutions**:

- Verify the `model_folder` value is correct: `checkpoints`, `diffusion_models`, or `unet`
- Check that model files exist in the folder for the selected category
- Ensure ComfyUI has been restarted after adding new models
- Hit the **Refresh** UI button if new models were added during a session
- If using `checkpoint_filter`, try without a filter first to see all available models

### Model Not Listed Even After Adding Files

**Problem**: Added new model files but they don't appear in the rotation.

**Solutions**:

- The model list discovers models at node initialization via ComfyUI's `folder_paths`
- If you add files during a session, you may need to hit the **Refresh** button in ComfyUI's UI
- On fresh startup, all models registered in `folder_paths` across ALL roots are discovered (local + ComfyUI-Shared)
- Ensure the model file has a supported extension: `.safetensors`, `.ckpt`, `.pt`, `.pth`

### Checkpoint Not Changing

**Problem**: Same model used for all images

**Solutions**:

- Verify `batch_index` is incrementing (check counter output)
- Set KSampler `batch_size: 1` (batches of images use same model)
- Set `change_interval` is less than total images
- Check that multiple models exist in the selected folder/category
- If using `model_folder: diffusion_models` or `unet`, ensure clip/vae are provided by separate loaders

### clip=None Error Downstream

**Problem**: Runtime error "clip input is invalid: None" when connecting the rotation node's clip output

**Solutions**:

- **Do not** connect the rotation node's `clip` output when `model_folder` is `diffusion_models` or `unet`
- Use a separate `CLIPLoader` node to provide the text encoder
- The node's info string warns about this — look for the "diffusion models have no embedded CLIP" message
- If you must use the clip output, stick to `model_folder: checkpoints` where clip is populated

### Path/Import Errors on Startup

**Problem**: Module import errors when starting ComfyUI

**Solutions**:

- Ensure all files are in correct locations within `ComfyUI/custom_nodes/`
- Restart ComfyUI completely (not just reload)
- Check Python path has no special characters or spaces
- Verify file permissions are correct

### Model Loading Errors

**Problem**: "Failed to load model" errors

**Solutions**:

- Verify model files are not corrupted
- Ensure sufficient disk space
- Check that the model is compatible with your ComfyUI version
- Try loading the model manually with the default loader first

## Folder Structure

```
comfyui-model-rotation/
├── __init__.py              # Main node registration, version 2.0.0
├── CHANGELOG.md             # Version history
├── nodes/
│   ├── __init__.py
│   ├── checkpoint_rotation.py       # Main rotation logic (advanced)
│   ├── rotation_with_counter.py   # Batch rotation with counter
│   ├── simple_rotation.py         # Simplified rotation
│   ├── simple_rotation_direct.py  # Direct index control
│   ├── checkpoint_filename.py     # Filename helper
│   ├── save_with_checkpoint.py    # Save with metadata + sidecar export
│   └── add_checkpoint_metadata.py # Metadata helper
├── utils/
│   ├── __init__.py
│   ├── model_discovery.py         # Model discovery & loading (new)
│   ├── secure_hash.py             # Salted hashing + manifest (new)
│   ├── version.py                 # Version resolved from the git history (new)
│   ├── attribution.py             # Author credits on every node (new)
│   ├── i18n.py                    # Multi-language support (new)
│   ├── language_config.json       # Saved language preference (new)
│   ├── secure_config.json         # Salt for the secure mode (new, auto-generated)
│   ├── checkpoint_utils.py        # Checkpoint operations
│   └── path_utils.py              # Path handling
├── tools/
│   ├── resolve_sidecar.py     # CLI to reverse an obfuscated sidecar (new)
│   └── release.py             # Semantic version bump + tag (new)
├── VERSION                    # Last released version (new)
├── tests/                     # pytest suite (new)
├── examples/
│   └── example_workflow.json    # Example workflow
├── README.md                  # This file
├── IMPLEMENTATION_PLAN.md       # Development plan
└── QUICKSTART.md              # Quick start guide
```

## Technical Details

### Languages (i18n)

The node strings, placeholders and help texts are translated. The default is
**Português (ptbr)**; English and Chinese are also available.

The choice is stored in `utils/language_config.json`:

```json
{
  "language": "pt"
}
```

Changing it at runtime:

```python
from utils.i18n import set_language, get

set_language("en")   # or "pt", "zh"
print(get("model_folder_label", "checkpoint_rotation"))  # -> "Model category:"
```

A missing or corrupted config falls back to ptbr automatically.

### How Rotation Works

The node calculates which model to use based on:

```python
rotation_index = (batch_index // change_interval) % num_models
```

**Example**: 5 models available: `[A, B, C, D, E]`
- `change_interval = 4`
- Batch indices 0-3: model A
- Batch indices 4-7: model B
- Batch indices 8-11: model C
- And so on...

### Supported File Types

- `.safetensors` (recommended)
- `.ckpt`
- `.pt`
- `.pth`

### Performance Notes

- **Discovery**: Model lists are discovered at node init via ComfyUI's `folder_paths`, scanning all registered roots
- **Caching**: Per-node cache removed — model list freshness follows ComfyUI standard (UI Refresh button)
- **Memory**: Only one model loaded at a time
- **Scanning**: Recursive folder scanning may be slow with very many files (typically < 50 models, fine)

### Discovery Across Roots

The node uses `folder_paths.get_filename_list(category)` which automatically discovers models across **all** registered ComfyUI folder roots. This means:

- Local `models/checkroots/` ✓
- ComfyUI-Shared (`ComfyUI-Shared/models/`) ✓
- Any extra paths configured in `comfyui-instance-model-paths.yaml` ✓

This fixes the root cause of the original bug: the old node only scanned `get_folder_paths("checkpoints")[0]`, which was the local Krea2 folder (empty). The new discovery scans all roots.

## Roadmap / Future Features

- [x] **Diffusion model support** — `model_folder` dropdown + `clip=None`/vae=None for diffusion categories
- [ ] Visual checkpoint selector UI
- [ ] Checkpoint preview thumbnails
- [ ] Weighted rotation (use some models more than others)
- [ ] Conditional rotation based on quality metrics
- [ ] Multi-folder support within a category
- [ ] Checkpoint metadata display in EXIF
- [ ] Generation history tracking
- [ ] Integration with ComfyUI Manager
- [ ] Weighted random selection

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Support

- **Issues**: Report bugs on [GitHub Issues](https://github.com/alvaronavega/comfyui-model-rotation/issues)
- **Discussions**: Ask questions in GitHub Discussions
- **ComfyUI Discord**: Get help from the community

## Versioning

The version of the package is **derived from the git history**, so it always
tells you exactly which code produced an image.

```
2.0.0                 exactly on the tag v2.0.0, clean tree
2.0.0+21.gd8477fc      21 commits after v2.0.0 (commit d8477fc)
2.0.0+21.gd8477fc.dirty  ... and the working tree has uncommitted changes
2.1.0-rc.1+3.gabc1234  a prerelease tag
```

It is a Semantic Version with the commit information in the build metadata
(also a valid PEP 440 local version).

### Where the version comes from

| Priority | Source | When it is used |
|----------|--------|-----------------|
| 1 | `git describe --tags --long --dirty` | a normal git checkout |
| 2 | the committed `VERSION` file | a ZIP download (no `.git` folder) |
| 3 | `0.0.0+unknown` | last resort |

### Where the version shows up

* the console banner: `Version: 2.0.0+21.gd8477fc  (tag: v2.0.0)  (commit: d8477fc)`
* `__init__.py`: `__version__` and `__version_info__` (a dict with the parsed parts)
* every node class: `VERSION` and `VERSION_INFO` attributes
* **the PNG metadata**: the `node_version` and `node_version_info` fields
* **the sidecar** (`.txt` / `.json`): the `node_version` field

The last two let a validator trace every file back to the exact build that
produced it. Turn the stamp off with `stamp_version: false` on the save node.

### Releasing

```bash
python tools/release.py show      # current state
python tools/release.py patch     # 2.0.0 -> 2.0.1
python tools/release.py minor     # 2.0.0 -> 2.1.0
python tools/release.py major     # 2.0.0 -> 3.0.0
python tools/release.py set 2.5.0 # explicit version
```

The helper refuses to run with a dirty working tree, updates the `VERSION`
file, creates the commit and the annotated tag, and prints the command to
publish it:

```
git push origin HEAD v2.1.0
```

### The semantic policy

| Bump | When |
|------|------|
| **MAJOR** | a node class id is removed or renamed, a `RETURN_TYPES` changes, or the widget order changes (existing graphs stop working) |
| **MINOR** | a new node, a new widget or a new option is added |
| **PATCH** | a bug fix, documentation, tests or an internal refactor |

---

## License

MIT License — see the [LICENSE](LICENSE) file for the full text, which credits
both the original author and the author of this fork.

## Credits & Acknowledgements

This project is a **fork** of the original *comfyui-change-checkpoint-randomly*
node. The original work is credited in full, and the modifications of this fork
are credited separately.

### Original project

- **Project**: [comfyui-change-checkpoint-randomly](https://github.com/trunksn1/comfyui-change-checkpoint-randomly)
- **Author**: [trunksn1](https://github.com/trunksn1)
- **License**: MIT
- Everything that existed before this fork — the rotation logic, the counter
  nodes, the metadata saver, the docs and the examples — comes from that project
  and its author. Thank you for the original work.

### This fork

- **Project**: [comfyui-model-rotation](https://github.com/alvaronavega/comfyui-model-rotation)
- **Author**: **Alvaro Navega** — <alvaroflaviano@hotmail.com>
- **License**: MIT (same as the original)
- The modifications of this fork are listed in the [CHANGELOG](CHANGELOG.md):

  - support for **diffusion models** (UNETs without embedded CLIP) through the
    `model_folder` dropdown
  - **cross-root model discovery** (all registered ComfyUI folder roots, not
    just the first one) — fixes the "No checkpoints found" failure
  - **explicit model selection** (`select_models`) to compare only the models
    you name
  - **clear error messages** instead of the silent `clip=None` return
  - a fully **configurable save node** with `.txt` / `.json` sidecars, filename
    wildcards, alternative output folder and a **secure mode** (salted hashes
    plus a private manifest)
  - a **workflow sanitizer** so local paths never leak into the PNG metadata
  - **multi-language** node texts (ptbr, en, zh)
  - a **test suite** and the `tools/resolve_sidecar.py` helper

### Inspiration

- The **Krea2** instance workflow configuration, which showed how a diffusion
  model setup has to be wired (separate `CLIPLoader` + `VAELoader`).

### How the credit appears in the code

* every node class exposes `AUTHOR`, `AUTHOR_EMAIL`, `ORIGINAL_PROJECT`,
  `ORIGINAL_AUTHOR` and `ORIGINAL_URL`
* every node docstring (the text shown as the node help) ends with the credit
* the console banner printed at load time names both the author and the
  original project

## Changelog

### Version 2.0.0 (2026-10-23)

- **Core**: Added `model_folder` dropdown (`checkpoints` | `diffusion_models` | `unet`) to all loader nodes
- **Discovery**: Model discovery now scans ALL registered ComfyUI folder roots via `folder_paths`, fixing the "No checkpoints found" bug
- **Loading**: `diffusion_models`/`unet` categories return `(model, None, None)` — clip/vae are `None`; users provide separate CLIPLoader/VAELoader
- **Error handling**: Clear `ModelNotFoundError` raises instead of silently returning `None` tuples
- **Savers**: `SaveImageWithCheckpoint` and `AddCheckpointToMetadata` resolve model names across categories
- **Nodes**: All 5 loader variants updated (`CheckpointRotationWithCounter`, `SimpleCheckpointRotation`, `CheckpointRotationSimple`, plus advanced `CheckpointRotationNode`)
- **Branding**: Version bump to 2.0.0, README/CHANGELOG updated
- **Backward compatibility**: Class IDs and `RETURN_TYPES` unchanged — existing graphs continue to work

### Version 1.0.0 (2025-11-05)

- Initial release
- Checkpoint rotation with multiple modes
- Batch index tracking
- Subfolder and filter support
- Comprehensive documentation