"""
Test the authorship attribution.

Verifies:
- every registered node exposes the AUTHOR attributes
- the docstring of every node mentions the author and the original project
- the package metadata carries the same information
"""

import importlib.util
import os

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NODE_CLASSES = [
    ("nodes.checkpoint_rotation", "CheckpointRotationNode"),
    ("nodes.rotation_with_counter", "CheckpointRotationWithCounter"),
    ("nodes.simple_rotation", "SimpleCheckpointRotation"),
    ("nodes.simple_rotation_direct", "CheckpointRotationSimple"),
    ("nodes.save_with_checkpoint", "SaveImageWithCheckpoint"),
    ("nodes.add_checkpoint_metadata", "AddCheckpointToMetadata"),
    ("nodes.checkpoint_filename", "CheckpointFilename"),
    ("nodes.batch_counter", "BatchIndexCounter"),
    ("nodes.batch_counter", "SimpleCounter"),
]


@pytest.mark.parametrize("module_name,class_name", NODE_CLASSES)
def test_node_has_author_attribute(module_name, class_name):
    """Every node must expose the authorship attributes."""
    module = importlib.import_module(module_name)
    node = getattr(module, class_name)

    assert node.AUTHOR == "Alvaro Navega"
    assert node.AUTHOR_EMAIL == "alvaroflaviano@hotmail.com"
    assert node.ORIGINAL_PROJECT == "comfyui-change-checkpoint-randomly"
    assert node.ORIGINAL_AUTHOR == "trunksn1"
    assert node.ORIGINAL_URL.startswith("https://github.com/trunksn1/")


@pytest.mark.parametrize("module_name,class_name", NODE_CLASSES)
def test_node_docstring_carries_the_credit(module_name, class_name):
    """The docstring (shown as the node help) must carry the credit."""
    module = importlib.import_module(module_name)
    node = getattr(module, class_name)
    doc = node.__doc__ or ""

    assert "Alvaro Navega" in doc, f"{class_name} docstring is missing the author"
    assert "trunksn1" in doc, f"{class_name} docstring is missing the original author"
    assert "comfyui-change-checkpoint-randomly" in doc


def test_package_metadata():
    """The package metadata must carry the same attribution."""
    init_path = os.path.join(REPO, "__init__.py")
    with open(init_path, encoding="utf-8") as fh:
        source = fh.read()

    assert '__author__ = "Alvaro Navega"' in source
    assert '__original_author__ = "trunksn1"' in source
    assert "trunksn1/comfyui-change-checkpoint-randomly" in source


def test_license_credits_both():
    """The LICENSE must mention both the original author and the fork author."""
    with open(os.path.join(REPO, "LICENSE"), encoding="utf-8") as fh:
        license_text = fh.read()

    assert "trunksn1" in license_text, "LICENSE must credit the original author"
    assert "Alvaro Navega" in license_text, "LICENSE must credit the fork author"
    assert "MIT" in license_text


def test_readme_credits_both():
    """The README must have a credits section naming both."""
    with open(os.path.join(REPO, "README.md"), encoding="utf-8") as fh:
        readme = fh.read()

    assert "## Credits" in readme
    assert "trunksn1" in readme
    assert "Alvaro Navega" in readme
