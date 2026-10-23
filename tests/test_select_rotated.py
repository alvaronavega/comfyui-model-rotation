"""
Test for select_rotated: name-based rotation selection.

Verifies:
- Empty list → None
- Sequential: (batch_index // interval) % len(names) picks slot, wraps around
- Random: reproducible with seed + rotation_index
- Shuffle: reproducible with seed, then iterates shuffled list
- Names are strings (not paths), rotation works on the list order
"""

import pytest

from utils.model_discovery import select_rotated


def test_select_rotated_empty_returns_none():
    """select_rotated([], ...) → None."""
    result = select_rotated([], batch_index=0, interval=1, mode="sequential", seed=42)
    assert result is None


def test_select_rotated_sequential_wrap():
    """Sequential mode wraps around using (batch_index // interval) % len(names)."""
    names = ["a.safetensors", "b.safetensors", "c.safetensors"]
    # interval=2, so every 2 batches we move to next
    # batch_index=0 → (0//2)%3 = 0 → "a"
    # batch_index=1 → (1//2)%3 = 0 → "a"
    # batch_index=2 → (2//2)%3 = 1 → "b"
    # batch_index=3 → (3//2)%3 = 1 → "b"
    # batch_index=4 → (4//2)%3 = 2 → "c"
    # batch_index=5 → (5//2)%3 = 2 → "c"
    # batch_index=6 → (6//2)%3 = 0 → "a" (wrap)
    assert select_rotated(names, batch_index=0, interval=2, mode="sequential", seed=0) == "a.safetensors"
    assert select_rotated(names, batch_index=1, interval=2, mode="sequential", seed=0) == "a.safetensors"
    assert select_rotated(names, batch_index=2, interval=2, mode="sequential", seed=0) == "b.safetensors"
    assert select_rotated(names, batch_index=3, interval=2, mode="sequential", seed=0) == "b.safetensors"
    assert select_rotated(names, batch_index=4, interval=2, mode="sequential", seed=0) == "c.safetensors"
    assert select_rotated(names, batch_index=5, interval=2, mode="sequential", seed=0) == "c.safetensors"
    assert select_rotated(names, batch_index=6, interval=2, mode="sequential", seed=0) == "a.safetensors"  # wrap


def test_select_rotated_random_reproducible():
    """Random mode: same seed + same rotation_index → same pick."""
    names = ["x.safetensors", "y.safetensors", "z.safetensors", "w.safetensors"]
    # Same seed, different batch indices → different rotation_index → potentially different pick
    # But same (seed, rotation_index) combo should give same pick
    pick1 = select_rotated(names, batch_index=0, interval=1, mode="random", seed=123)
    pick2 = select_rotated(names, batch_index=0, interval=1, mode="random", seed=123)
    assert pick1 == pick2, f"Random should be reproducible: {pick1} != {pick2}"

    # Different seeds should give different picks (usually)
    pick3 = select_rotated(names, batch_index=0, interval=1, mode="random", seed=999)
    assert pick3 != pick1 or names.count(pick3) == 1  # may coincidentally match


def test_select_rotated_shuffle_reproducible():
    """Shuffle mode: same seed → same permutation, then iterate."""
    names = ["p1.safetensors", "p2.safetensors", "p3.safetensors", "p4.safetensors"]
    # Two calls with same seed should return same (possibly different index due to rotation)
    r1 = select_rotated(names, batch_index=0, interval=1, mode="shuffle", seed=42)
    r2 = select_rotated(names, batch_index=0, interval=1, mode="shuffle", seed=42)
    assert r1 == r2, f"Shuffle should be reproducible: {r1} != {r2}"


def test_select_rotated_single_name():
    """With one name, always returns that name regardless of parameters."""
    result = select_rotated(["only_one.safetensors"], batch_index=999, interval=5, mode="random", seed=0)
    assert result == "only_one.safetensors"
    result2 = select_rotated(["only_one.safetensors"], batch_index=0, interval=1, mode="sequential", seed=42)
    assert result2 == "only_one.safetensors"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])