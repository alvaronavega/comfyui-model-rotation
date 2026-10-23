"""
Test for the secure hashing system (utils/secure_hash.py).

Verifies:
- hash_value is deterministic and salt-dependent
- a different salt produces different hashes (rainbow table protection)
- hash_mapping keeps the keys and hashes the values
- build_manifest / merge_manifest / save_manifest / load_manifest round-trip
- resolve_sidecar turns hashes back into the real values
- brute_force_known finds a value among candidates
"""

import json
import os

import pytest

from utils import secure_hash


@pytest.fixture(autouse=True)
def temp_salt(tmp_path, monkeypatch):
    """Use a throwaway salt + config path for every test."""
    cfg = tmp_path / "secure_config.json"
    monkeypatch.setattr(secure_hash, "CONFIG_PATH", str(cfg))
    monkeypatch.setattr(secure_hash, "_salt_cache", None)
    yield


def test_hash_is_deterministic():
    """The same value + salt must always give the same hash."""
    secure_hash.set_salt("my-secret-salt-1234")
    a = secure_hash.hash_value("krea2Softrealism_v10.safetensors")
    b = secure_hash.hash_value("krea2Softrealism_v10.safetensors")
    assert a == b
    assert len(a) == 12


def test_hash_changes_with_salt():
    """A different salt must produce a different hash (defeats rainbow tables)."""
    secure_hash.set_salt("salt-one-abcdefgh")
    first = secure_hash.hash_value("model.safetensors")

    secure_hash.set_salt("salt-two-ijklmnop")
    second = secure_hash.hash_value("model.safetensors")

    assert first != second, "hash must depend on the salt"


def test_different_values_give_different_hashes():
    secure_hash.set_salt("a-fixed-salt-value")
    assert secure_hash.hash_value("a") != secure_hash.hash_value("b")


def test_salt_is_persisted_and_reloaded(tmp_path, monkeypatch):
    """The salt must survive a restart."""
    cfg = tmp_path / "secure_config.json"
    monkeypatch.setattr(secure_hash, "CONFIG_PATH", str(cfg))
    secure_hash.set_salt("persistent-salt-value")
    salt = secure_hash.get_salt()

    # Simulate a new session
    monkeypatch.setattr(secure_hash, "_salt_cache", None)
    assert secure_hash.get_salt() == salt


def test_salt_is_generated_when_missing():
    """No config → a random salt is created and persisted."""
    salt = secure_hash.get_salt()
    assert len(salt) >= 32
    assert os.path.exists(secure_hash.CONFIG_PATH)


def test_set_salt_rejects_short_salt():
    with pytest.raises(ValueError):
        secure_hash.set_salt("abc")


def test_hash_mapping_keeps_keys():
    """Only the values are hashed; the keys survive."""
    secure_hash.set_salt("mapping-salt-value")
    original = {"seed": 12345, "model": "a.safetensors", "loras": ["l1", "l2"]}
    hashed = secure_hash.hash_mapping(original)

    assert set(hashed.keys()) == set(original.keys())
    assert hashed["seed"] != 12345
    assert hashed["loras"] == [secure_hash.hash_value("l1"), secure_hash.hash_value("l2")]


def test_manifest_round_trip(tmp_path):
    """The manifest maps hashes back to the real values."""
    secure_hash.set_salt("manifest-salt-value")
    original = {"seed": 42, "model": "krea2.safetensors"}
    hashed = secure_hash.hash_mapping(original)

    manifest = secure_hash.build_manifest(original, hashed)
    assert manifest[hashed["seed"]] == "42"
    assert manifest[hashed["model"]] == "krea2.safetensors"

    path = str(tmp_path / "manifest.json")
    secure_hash.save_manifest(manifest, path)
    loaded = secure_hash.load_manifest(path)
    assert loaded == manifest


def test_manifest_merge_keeps_existing(tmp_path):
    """Merging must not overwrite entries that already exist."""
    path = str(tmp_path / "manifest.json")
    secure_hash.save_manifest({"aaa": "first"}, path)
    merged = secure_hash.merge_manifest(secure_hash.load_manifest(path), {"aaa": "second", "bbb": "third"})
    assert merged["aaa"] == "first"
    assert merged["bbb"] == "third"


def test_resolve_sidecar_restores_values():
    """resolve_sidecar must turn the hashes back into the real values."""
    secure_hash.set_salt("resolve-salt-value")
    original = {"seed": 999, "model": "krea2.safetensors", "steps": 28}
    hashed = secure_hash.hash_mapping(original)
    manifest = secure_hash.build_manifest(original, hashed)

    resolved = secure_hash.resolve_sidecar(hashed, manifest)
    assert resolved["seed"] == "999"
    assert resolved["model"] == "krea2.safetensors"
    assert resolved["steps"] == "28"


def test_resolve_sidecar_leaves_unknown_values():
    """A hash that is not in the manifest stays as it is."""
    resolved = secure_hash.resolve_sidecar({"seed": "deadbeef1234"}, {})
    assert resolved["seed"] == "deadbeef1234"


def test_brute_force_known():
    """A hash can be matched against a small candidate list."""
    secure_hash.set_salt("brute-salt-value")
    target = secure_hash.hash_value("krea2WRC8_3210425.safetensors")
    found = secure_hash.brute_force_known(
        target,
        ["krea2Softrealism_v10.safetensors", "krea2WRC8_3210425.safetensors"],
    )
    assert found == "krea2WRC8_3210425.safetensors"


def test_brute_force_returns_none_when_absent():
    secure_hash.set_salt("brute-salt-value")
    target = secure_hash.hash_value("not-in-the-list")
    assert secure_hash.brute_force_known(target, ["a", "b"]) is None


def test_resolve_file(tmp_path):
    """resolve_file loads a sidecar and resolves it in one go."""
    secure_hash.set_salt("file-salt-value")
    original = {"model": "krea2.safetensors"}
    hashed = secure_hash.hash_mapping(original)
    manifest = secure_hash.build_manifest(original, hashed)

    sidecar = tmp_path / "img.json"
    sidecar.write_text(json.dumps(hashed), encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    secure_hash.save_manifest(manifest, str(manifest_path))

    resolved = secure_hash.resolve_file(str(sidecar), str(manifest_path))
    assert resolved["model"] == "krea2.safetensors"
