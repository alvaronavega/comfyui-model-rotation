"""
Small helper that injects the authorship metadata into every node class.

ComfyUI does not have a standard "author" field on nodes, so the credit is
carried in three places:

* a module level ``AUTHOR`` / ``ORIGINAL_PROJECT`` pair
* an ``AUTHOR`` class attribute on every node (readable by tools and by the
  ComfyUI Manager, which shows the repository author)
* the docstring of each node, which the frontend renders as the node help

Usage::

    from .utils.attribution import add_attribution

    class MyNode:
        '''Rotate through models.'''

    add_attribution(MyNode)
"""

# Author of this fork
AUTHOR = "Alvaro Navega"
AUTHOR_EMAIL = "alvaroflaviano@hotmail.com"

# The project this fork is based on
ORIGINAL_PROJECT = "comfyui-change-checkpoint-randomly"
ORIGINAL_AUTHOR = "trunksn1"
ORIGINAL_URL = "https://github.com/trunksn1/comfyui-change-checkpoint-randomly"

_CREDIT_LINE = (
    f"\n\n    Author: {AUTHOR} <{AUTHOR_EMAIL}>\n"
    f"    Based on {ORIGINAL_PROJECT} by {ORIGINAL_AUTHOR} ({ORIGINAL_URL})\n"
)


def add_attribution(node_class) -> None:
    """Attach the authorship metadata to *node_class* (in place)."""
    node_class.AUTHOR = AUTHOR
    node_class.AUTHOR_EMAIL = AUTHOR_EMAIL
    node_class.ORIGINAL_PROJECT = ORIGINAL_PROJECT
    node_class.ORIGINAL_AUTHOR = ORIGINAL_AUTHOR
    node_class.ORIGINAL_URL = ORIGINAL_URL

    # Version, resolved from the git history
    try:
        from utils.version import get_version, get_version_info
        node_class.VERSION = get_version()
        node_class.VERSION_INFO = get_version_info()
    except Exception:  # noqa: BLE001 - never break a node because of this
        node_class.VERSION = "unknown"
        node_class.VERSION_INFO = {}

    # Append the credit to the docstring so it shows up in the node help.
    doc = node_class.__doc__ or ""
    if "Based on" not in doc:
        node_class.__doc__ = doc.rstrip() + _CREDIT_LINE


__all__ = [
    "add_attribution",
    "AUTHOR",
    "AUTHOR_EMAIL",
    "ORIGINAL_PROJECT",
    "ORIGINAL_AUTHOR",
    "ORIGINAL_URL",
]
