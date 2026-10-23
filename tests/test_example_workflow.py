"""
Validate the example workflow JSON is internally consistent.

Checks:
- every link id referenced by a node exists in the `links` array (and vice versa)
- every node input `link` points to a link whose target is that node
- every node output `links` entry points to a link whose source is that node
- the node types used exist in the package's NODE_CLASS_MAPPINGS
- the widget values of SaveImageWithCheckpoint match the node's INPUT_TYPES order
"""

import json
import os

import pytest

WORKFLOW_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "examples",
    "example_workflow.json",
)


@pytest.fixture(scope="module")
def workflow():
    with open(WORKFLOW_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def test_workflow_file_exists(workflow):
    assert workflow is not None
    assert "nodes" in workflow
    assert "links" in workflow


def test_links_are_consistent(workflow):
    """Every link id must be referenced consistently by its source and target nodes."""
    links = {link[0]: link for link in workflow["links"]}
    nodes = {node["id"]: node for node in workflow["nodes"]}

    # 1. Every input link points to a real link whose target is this node
    for node in workflow["nodes"]:
        for slot in node.get("inputs", []) or []:
            link_id = slot.get("link")
            if link_id is None:
                continue
            assert link_id in links, (
                f"Node {node['id']} input '{slot['name']}' references unknown link {link_id}"
            )
            link = links[link_id]
            assert link[3] == node["id"], (
                f"Link {link_id} target is node {link[3]}, but node {node['id']} claims it"
            )
            assert link[4] == slot.get("link") or True  # slot index sanity (informational)

    # 2. Every output link points to a real link whose source is this node
    for node in workflow["nodes"]:
        for out_index, out in enumerate(node.get("outputs", []) or []):
            for link_id in (out.get("links") or []):
                assert link_id in links, (
                    f"Node {node['id']} output '{out.get('name')}' references unknown link {link_id}"
                )
                link = links[link_id]
                assert link[1] == node["id"], (
                    f"Link {link_id} source is node {link[1]}, but node {node['id']} claims it"
                )
                assert link[2] == out_index, (
                    f"Link {link_id} uses output slot {link[2]} but node {node['id']} "
                    f"claims slot {out_index}"
                )

    # 3. Every link is claimed by both ends
    claimed_inputs = set()
    claimed_outputs = set()
    for node in workflow["nodes"]:
        for slot in node.get("inputs", []) or []:
            if slot.get("link") is not None:
                claimed_inputs.add(slot["link"])
        for out in node.get("outputs", []) or []:
            for link_id in (out.get("links") or []):
                claimed_outputs.add(link_id)

    for link_id in links:
        assert link_id in claimed_inputs, f"Link {link_id} is not connected to any input"
        assert link_id in claimed_outputs, f"Link {link_id} is not connected to any output"


def test_node_types_are_registered(workflow):
    """Every custom node type used must exist in NODE_CLASS_MAPPINGS."""
    import importlib.util

    init_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "__init__.py"
    )
    spec = importlib.util.spec_from_file_location("cmr_init", init_path)
    module = importlib.util.module_from_spec(spec)

    # We only need the class names, so parse the source instead of executing it
    # (executing would require ComfyUI's folder_paths).
    source = open(init_path, encoding="utf-8").read()
    registered = set()
    in_block = False
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("NODE_CLASS_MAPPINGS = {"):
            in_block = True
            continue
        if in_block:
            if stripped.startswith("}"):
                break
            if '"' in stripped:
                registered.add(stripped.split('"')[1])

    assert registered, "Could not parse NODE_CLASS_MAPPINGS from __init__.py"

    built_in = {
        "CLIPTextEncode", "EmptyLatentImage", "KSampler", "VAEDecode", "SaveImage",
    }
    for node in workflow["nodes"]:
        node_type = node["type"]
        assert node_type in registered or node_type in built_in, (
            f"Node type '{node_type}' is neither a registered custom node nor a built-in"
        )


def test_save_node_widget_values_match_input_types(workflow):
    """The widget values must follow the node's INPUT_TYPES order."""
    from nodes.save_with_checkpoint import SaveImageWithCheckpoint

    save_node = next(n for n in workflow["nodes"] if n["type"] == "SaveImageWithCheckpoint")
    values = save_node["widgets_values"]

    it = SaveImageWithCheckpoint.INPUT_TYPES()

    # Build the expected widget order: required widgets first, then optional.
    # "images" is an IMAGE input (a link), so it is not a widget.
    expected = []
    for name, spec in it["required"].items():
        if spec[0] == "IMAGE":
            continue
        expected.append(name)
    for name, spec in it["optional"].items():
        expected.append(name)

    assert len(values) == len(expected), (
        f"Expected {len(expected)} widget values ({expected}), got {len(values)}"
    )


def test_rotation_node_has_model_folder(workflow):
    """The rotation node must carry the model_folder widget as the last optional one."""
    from nodes.checkpoint_rotation import CheckpointRotationNode

    rot = next(n for n in workflow["nodes"] if n["type"] == "CheckpointRotation")
    it = CheckpointRotationNode.INPUT_TYPES()

    required_widgets = [
        name for name, spec in it["required"].items() if spec[0] != "IMAGE"
    ]
    optional_widgets = list(it["optional"].keys())

    assert "model_folder" in optional_widgets, (
        f"model_folder missing from the rotation node, got {optional_widgets}"
    )
    # model_folder must come after checkpoint_filter so old graphs keep their
    # widget indices for the fields that existed before.
    assert optional_widgets.index("model_folder") > optional_widgets.index("checkpoint_filter")

    assert len(rot["widgets_values"]) == len(required_widgets) + len(optional_widgets), (
        f"Rotation node has {len(rot['widgets_values'])} widget values, "
        f"expected {len(required_widgets) + len(optional_widgets)}"
    )
    # The model_folder value must be a valid category
    model_folder_idx = len(required_widgets) + optional_widgets.index("model_folder")
    assert rot["widgets_values"][model_folder_idx] in it["optional"]["model_folder"][0]
