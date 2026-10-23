"""
Generate the PUBLIC example files that ship with the repository.

These files are committed to git on purpose: they show exactly what the
secure mode produces without exposing any real data.  A fixed, well-known
salt is used so that anyone can reproduce the hashes and verify the example.

Usage:
    python examples/secure_mode/generate_example.py
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO)

from utils.secure_hash import HASH_LENGTH, hash_mapping  # noqa: E402

# A fixed salt so the example is reproducible for everyone.
EXAMPLE_SALT = "exemplo-salt-comfyui-model-rotation"

# The fake generation data used in the example.
ORIGINAL = {
    "positive_prompt": "retrato de uma mulher, luz dourada",
    "negative_prompt": "blurry, low quality",
    "checkpoint": "krea2Softrealism_v10.safetensors",
    "seed": 777888,
    "steps": 28,
    "cfg": 4.5,
    "sampler_name": "dpmpp_2m",
    "scheduler": "karras",
    "vae": "qwen_image_vae.safetensors",
    "clip": "qwen3vl_4b_int8_convrot.safetensors",
    "loras": ["style_lora.safetensors"],
}


def main() -> None:
    hashed = hash_mapping(ORIGINAL, salt=EXAMPLE_SALT, length=HASH_LENGTH)

    # The manifest maps every hash back to its real value.
    manifest = {}
    for key, real in ORIGINAL.items():
        if isinstance(real, list):
            for item in hashed[key]:
                manifest[item] = item  # placeholder, fixed below
        else:
            manifest[hashed[key]] = str(real)
    for item, hashed_item in zip(ORIGINAL["loras"], hashed["loras"]):
        manifest[hashed_item] = item

    # 1) The obfuscated sidecar (json)
    sidecar_json = os.path.join(HERE, "example_sidecar.json")
    with open(sidecar_json, "w", encoding="utf-8") as fh:
        json.dump(hashed, fh, ensure_ascii=False, indent=4)

    # 2) The obfuscated sidecar (txt)
    sidecar_txt = os.path.join(HERE, "example_sidecar.txt")
    with open(sidecar_txt, "w", encoding="utf-8") as fh:
        for key, value in hashed.items():
            fh.write(f"{key}: {value}\n")

    # 3) The manifest (the private key that reverses it)
    manifest_path = os.path.join(HERE, "example_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=4)

    # 4) The salt used to produce the example
    salt_path = os.path.join(HERE, "example_salt.txt")
    with open(salt_path, "w", encoding="utf-8") as fh:
        fh.write(EXAMPLE_SALT + "\n")

    print("Example files written to", HERE)
    print()
    print("sidecar (obfuscated):")
    for key, value in hashed.items():
        print(f"  {key}: {value}")
    print()
    print("manifest (reverses it):")
    for key, value in manifest.items():
        print(f"  {key} -> {value}")


if __name__ == "__main__":
    main()
