# Secure mode — example files

Everything in this folder is **public and safe to commit**. It contains fake
data only. It shows exactly what the `secure_mode` of the
**Save Image (Metadata & Export)** node produces, and how to reverse it.

## The files

| File | What it is |
|------|------------|
| `example_sidecar.json` | The obfuscated sidecar, as written by the node (JSON) |
| `example_sidecar.txt` | The same sidecar in text format |
| `example_manifest.json` | The **manifest**: the `hash → real value` map that reverses the sidecar |
| `example_salt.txt` | The salt used to produce this example (fixed, so it is reproducible) |
| `generate_example.py` | The script that regenerates all of the above |

## Reproduce the example

```bash
python examples/secure_mode/generate_example.py
```

## Reverse the example

```bash
python tools/resolve_sidecar.py single \
    examples/secure_mode/example_sidecar.json \
    examples/secure_mode/example_manifest.json
```

Output:

```json
{
  "positive_prompt": "retrato de uma mulher, luz dourada",
  "negative_prompt": "blurry, low quality",
  "checkpoint": "krea2Softrealism_v10.safetensors",
  "seed": "777888",
  "steps": "28",
  "cfg": "4.5",
  "sampler_name": "dpmpp_2m",
  "scheduler": "karras",
  "vae": "qwen_image_vae.safetensors",
  "clip": "qwen3vl_4b_int8_convrot.safetensors",
  "loras": ["style_lora.safetensors"]
}
```

## Reverse a hash without the manifest

When you know the candidate values (the model list is small), brute force works:

```bash
python tools/resolve_sidecar.py brute 1313449c28d7 examples/secure_mode/modelos_exemplo.txt
# -> FOUND: krea2Softrealism_v10.safetensors
```

## How it works

```
salt  ──┐
        ├──> sha256(salt + "||" + value) ──> first 12 hex chars ──> the hash
value ──┘
```

* The **salt** lives in `utils/secure_config.json`. It is generated
  automatically on first use and is **never** committed to git.
* The **manifest** is the private dictionary `hash → real value`. It is
  written by the node wherever you point `manifest_path`, and it is the only
  thing that makes the sidecar reversible.

Because the hash is salted, somebody who only has the sidecar cannot rebuild
a rainbow table of the possible values.

## What to keep private in your own install

| File | Keep it? | Where it is |
|------|-----------|-------------|
| `utils/secure_config.json` (the salt) | **yes** | inside the node, git-ignored |
| your `manifest.json` | **yes**, and back it up | wherever you point `manifest_path` |
| the sidecars | free to share | next to the images |

Losing the manifest means the sidecars become permanently unreadable — that
is on purpose. Losing the salt means the hashes can no longer be recomputed
either.
