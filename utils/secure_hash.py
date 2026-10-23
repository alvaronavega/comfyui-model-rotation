"""
Secure hashing helpers for comfyui-model-rotation.

The `secure_mode` of SaveImageWithCheckpoint replaces every value of the
generation sidecar with a short hash.  SHA-256 is a one-way function, so the
value cannot be "decrypted" from the hash alone.  This module provides the two
things that make the sidecar useful again for the owner:

1. **Salt (pepper)** — a secret string mixed into every hash.  Without it, an
   attacker could rebuild a rainbow table of the (small) set of model names.
   The salt lives in ``utils/secure_config.json`` and is never written to the
   sidecar.

2. **Manifest (reverse lookup)** — a private JSON file mapping
   ``hash -> real value``.  It is written next to the images only when the user
   provides a manifest path, and it is what lets the owner resolve a sidecar
   back into readable data later.

Typical flow::

    from utils.secure_hash import hash_value, resolve_sidecar

    h = hash_value("krea2Softrealism_v10.safetensors")   # -> "7de09c064983"
    resolve_sidecar(sidecar_dict)                        # -> real values back
"""

import json
import os
from typing import Any, Dict, Iterable, List, Optional

# Config file that holds the salt (never shipped to the sidecars)
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "secure_config.json")

# Default length of the generated hash fragments
HASH_LENGTH = 12

# In-memory cache for the salt
_salt_cache: Optional[str] = None


# ── Salt management ─────────────────────────────────────────────────────────

def get_salt() -> str:
    """Return the current salt, creating one on first use.

    The salt is generated randomly and persisted in ``secure_config.json``.
    Losing that file means previously written sidecars can no longer be
    resolved (the hashes would need to be recomputed with the new salt).
    """
    global _salt_cache
    if _salt_cache is not None:
        return _salt_cache

    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            salt = data.get("salt")
            if salt:
                _salt_cache = salt
                return salt
    except (json.JSONDecodeError, KeyError, TypeError, OSError):
        pass

    # Create a new random salt
    import secrets
    salt = secrets.token_hex(32)
    set_salt(salt)
    _salt_cache = salt
    return salt


def set_salt(salt: str) -> None:
    """Persist a custom salt to the config file."""
    global _salt_cache
    if not salt or len(salt) < 8:
        raise ValueError("The salt must be at least 8 characters long")
    folder = os.path.dirname(os.path.abspath(CONFIG_PATH))
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
        json.dump({"salt": salt}, fh, ensure_ascii=False, indent=2)
    _salt_cache = salt


def rotate_salt() -> str:
    """Generate and persist a brand new salt (invalidates old manifests)."""
    global _salt_cache
    import secrets
    salt = secrets.token_hex(32)
    set_salt(salt)
    return salt


# ── Hashing ─────────────────────────────────────────────────────────────────

def hash_value(value: Any, salt: Optional[str] = None, length: int = HASH_LENGTH) -> str:
    """Hash *value* with the project salt and return a short hex fragment.

    Args:
        value: Any value (str, int, float...). Lists are hashed item by item
               by the caller, so this always receives a scalar.
        salt: Optional explicit salt; defaults to the configured one.
        length: Number of hex characters to keep.

    Returns:
        Lowercase hex string of ``length`` characters.
    """
    import hashlib

    if salt is None:
        salt = get_salt()

    text = f"{salt}||{value}"
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return digest[:length]


def hash_mapping(values: Dict[str, Any], salt: Optional[str] = None,
                 length: int = HASH_LENGTH) -> Dict[str, Any]:
    """Hash every value of *values*, keeping the keys untouched."""
    result: Dict[str, Any] = {}
    for key, value in values.items():
        if isinstance(value, list):
            result[key] = [hash_value(item, salt, length) for item in value]
        else:
            result[key] = hash_value(value, salt, length)
    return result


# ── Manifest (reverse lookup) ──────────────────────────────────────────────

def build_manifest(original: Dict[str, Any], hashed: Dict[str, Any],
                   salt: Optional[str] = None,
                   length: int = HASH_LENGTH) -> Dict[str, str]:
    """Build the ``hash -> real value`` mapping for one sidecar.

    Only the pairs that actually differ (i.e. were hashed) are included.
    """
    manifest: Dict[str, str] = {}
    for key, real_value in original.items():
        hashed_value = hashed.get(key)
        if isinstance(real_value, list) and isinstance(hashed_value, list):
            for real_item, hashed_item in zip(real_value, hashed_value):
                manifest[hashed_item] = str(real_item)
        elif hashed_value is not None and hashed_value != real_value:
            manifest[str(hashed_value)] = str(real_value)
    return manifest


def merge_manifest(manifest: Dict[str, str], new_entries: Dict[str, str]) -> Dict[str, str]:
    """Merge *new_entries* into *manifest* (existing entries win)."""
    merged = dict(new_entries)
    merged.update(manifest)
    return merged


def save_manifest(manifest: Dict[str, str], path: str) -> None:
    """Write the manifest to *path* as JSON (private file — keep it safe)."""
    folder = os.path.dirname(os.path.abspath(path))
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=4)


def load_manifest(path: str) -> Dict[str, str]:
    """Read a manifest file.  Returns an empty dict when it does not exist."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
    except (json.JSONDecodeError, OSError):
        pass
    return {}


# ── Resolution ─────────────────────────────────────────────────────────────

def resolve_sidecar(data: Dict[str, Any], manifest: Dict[str, str]) -> Dict[str, Any]:
    """Replace every hash in *data* with its real value using *manifest*.

    Values that are not in the manifest are left untouched, so you can tell
    which entries could (and could not) be resolved.
    """
    resolved: Dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, list):
            resolved[key] = [manifest.get(str(item), item) for item in value]
        elif isinstance(value, str):
            resolved[key] = manifest.get(value, value)
        else:
            resolved[key] = value
    return resolved


def resolve_file(sidecar_path: str, manifest_path: str) -> Dict[str, Any]:
    """Load a .json sidecar and resolve it against a manifest file."""
    with open(sidecar_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return resolve_sidecar(data, load_manifest(manifest_path))


def brute_force_known(value: str, candidates: Iterable[str], salt: Optional[str] = None) -> Optional[str]:
    """Try to find *value* among *candidates* by hashing each one.

    Handy when you know the model list: there are only a handful of candidate
    names, so the hash can be matched even without the manifest.
    """
    for candidate in candidates:
        if hash_value(candidate, salt) == value:
            return candidate
    return None
