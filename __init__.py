"""ComfyUI Model Rotation

A custom node for ComfyUI that enables automatic rotation through checkpoints
or diffusion models (UNETs without embedded CLIP) during batch generation.

Enables the Krea2 instance to use custom model rotation with diffusion-style
models that have no embedded CLIP — users provide CLIPLoader and VAELoader
separately in their workflow, as in the working Krea2 configuration.

Author:  Alvaro Navega <alvaroflaviano@hotmail.com>
Version: 2.0.0

Based on the original "comfyui-change-checkpoint-randomly" project by
trunksn1 — https://github.com/trunksn1/comfyui-change-checkpoint-randomly
See the Credits section of the README for the full attribution.
"""

import os
import sys
import traceback

# Version info
__version__ = "2.0.0"
__author__ = "Alvaro Navega"
__author_email__ = "alvaroflaviano@hotmail.com"
__license__ = "MIT"

# Attribution to the original project this fork is based on
__original_project__ = "comfyui-change-checkpoint-randomly"
__original_author__ = "trunksn1"
__original_url__ = "https://github.com/trunksn1/comfyui-change-checkpoint-randomly"

# Add this directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Initialize empty mappings in case of import failure
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}
WEB_DIRECTORY = "./web"

try:
    # Import node classes using relative imports to avoid conflict with ComfyUI's 'nodes' module
    from .nodes.checkpoint_rotation import CheckpointRotationNode
    from .nodes.batch_counter import BatchIndexCounter, SimpleCounter
    from .nodes.simple_rotation import SimpleCheckpointRotation
    from .nodes.rotation_with_counter import CheckpointRotationWithCounter
    from .nodes.simple_rotation_direct import CheckpointRotationSimple
    from .nodes.checkpoint_filename import CheckpointFilename
    from .nodes.save_with_checkpoint import SaveImageWithCheckpoint

    # Node class mappings for ComfyUI
    NODE_CLASS_MAPPINGS = {
        "CheckpointRotationWithCounter": CheckpointRotationWithCounter,  # ⭐ MAIN NODE
        "SaveImageWithCheckpoint": SaveImageWithCheckpoint,  # ⭐ USE FOR PROPER METADATA
        "CheckpointFilename": CheckpointFilename,
        "CheckpointRotationSimple": CheckpointRotationSimple,
        "SimpleCheckpointRotation": SimpleCheckpointRotation,
        "CheckpointRotation": CheckpointRotationNode,
        "BatchIndexCounter": BatchIndexCounter,
        "SimpleCounter": SimpleCounter,
    }

    # Display names for nodes in ComfyUI interface
    NODE_DISPLAY_NAME_MAPPINGS = {
        "CheckpointRotationWithCounter": "Checkpoint Rotation (Batch)",  # ⭐ USE THIS
        "SaveImageWithCheckpoint": "Save Image (Metadata & Export)",  # ⭐ USE THIS
        "CheckpointFilename": "Checkpoint to Filename",
        "CheckpointRotationSimple": "Checkpoint Rotation (Debug)",
        "SimpleCheckpointRotation": "Simple Checkpoint Rotation",
        "CheckpointRotation": "Checkpoint Rotation Loader (Advanced)",
        "BatchIndexCounter": "Batch Index Counter",
        "SimpleCounter": "Simple Counter",
    }

    # ── ASCII ART BANNER ─────────────────────────────────────────────────────
    BANNER = r"""
╔═══════════════════════════════════════════════════════════════════╗
║ ██████╗ ██████╗  ██████╗ ██████╗  ██████╗ ██████╗  ██████╗ ███████╗ ║
║ ██╔══██╗██╔══██╗██╔══██╗██╔══██╗██╔══██╗██╔══██╗██╔══██╗██╔════╝ ║
║ ██████╔╝██████╔╝██████╔╝██████╔╝██████╔╝██████╔╝██████╔╝█████╗   ║
║ ██╔══██╗██╔══██╗██╔══██╗██╔══██╗██╔══██╗██╔══██╗██╔════╝ ██╔══╝   ║
║ ██████╔╝██║  ██║██║  ██║██║  ██║██║  ██║██║  ██║██║  ███╗███████╗ ║
║ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚══════╝ ║
║   ComfyUI Model Rotation Node v2.0.0                            ║
╚═══════════════════════════════════════════════════════════════════╝
    """

    # ── MENSAGENS DE CARREGAMENTO ───────────────────────────────────────────
    LOAD_MESSAGES = [
        "   Carregando módulo de descoberta de modelos...",
        "   Inicializando varredura cross-root via folder_paths...",
        "   Detectando modelos em todas as pastas registradas (local + Shared)...",
        "   Configurando dropdown model_folder: checkpoints | diffusion_models | unet",
        "   Habilitando suporte a diffusion models (sem CLIP embutido)...",
        "   Configurando salvamento de metadado cross-categorical...",
        "   Carregando nós de suporte: Batch Index Counter, Simple Counter...",
        "   Pronto! Use o nó Checkpoint Rotation (Batch) para iniciar a rotação.",
    ]

    # Print banner
    print(BANNER)

    # Print loading messages
    print()
    for msg in LOAD_MESSAGES:
        print(msg)

    # Print success message
    print()
    print("\033[92m[ComfyUI] Checkpoint Rotation Node loaded successfully!\033[0m")
    print(f"  ⭐ Checkpoint Rotation (Batch) - Main node")
    print(f"  ⭐ Save Image (Metadata & Export) - Save PNG + .txt/.json sidecar with the generation data")
    print(f"  - Checkpoint to Filename - Add checkpoint to filename")
    print(f"  - Diffusion models: use with separate CLIPLoader + VAELoader (no embedded CLIP)")
    print(f"  Version: {__version__}")
    print()
    print(f"  \033[96mAuthor:\033[0m {__author__} <{__author_email__}>")
    print(f"  \033[96mBased on:\033[0m {__original_project__} by {__original_author__}")
    print(f"               {__original_url__}")

except Exception as e:
    print("\033[91m[ComfyUI] ERROR: Failed to load Checkpoint Rotation Node!\033[0m")
    print(f"  Error: {str(e)}")
    print(f"  Location: {current_dir}")
    print("\033[91m  Full traceback:\033[0m")
    traceback.print_exc()
    print("\033[93m  Please report this error with the traceback above.\033[0m")

# Export for ComfyUI
__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']