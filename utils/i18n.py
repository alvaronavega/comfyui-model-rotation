"""
Internationalization (i18n) module for comfyui-model-rotation.

Provides multi-language support for node strings, tooltips, and help texts.
Supports auto-persisting the language choice to a config file.

Default language: Portuguese (ptbr)
Available languages: Portuguese (ptbr), English (en), Chinese (zh_cn)
"""

import json
import os
from typing import Dict, List, Optional

# Idiomas disponíveis com nomes em português para a UI
LANGUAGES = {
    "pt": "Português (ptbr)",
    "en": "English",
    "zh": "中文 (Chinese)",
}

# Idioma padrão do projeto (ptbr)
DEFAULT_LANGUAGE = "pt"

# Caminho do arquivo de configuração (na pasta utils/)
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "language_config.json")

# Idioma atual — definido ao importar o módulo (lê o config)
current_language: str = DEFAULT_LANGUAGE  # default: ptbr

# Dicionário de traduções: {node_name: {language_code: translated_text}}
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    # ── Node: Checkpoint Rotation (Batch) ──────────────────────────────────
    "checkpoint_rotation": {
        "pt": {
            "model_folder_label": "Categoria de modelo:",
            "model_folder_tooltip": "checkpoints = com CLIP/VAE embutido\n diffusion_models/unet = sem CLIP/VAE (requer CLIPLoader/VAELoader separado)",
            "checkpoint_filter_label": "Filtrar por nome:",
            "info_title": "Informações da rotação:",
            "subfolder_placeholder": "subfolder path (leave empty for root)",
            "change_interval_tooltip": "Number of images before switching model",
            "batch_index_tooltip": "Current batch index (use BatchIndexCounter)",
            "rotation_mode_tooltip": "How to select next model",
            "seed_tooltip": "Seed for random/shuffle modes",
            "checkpoint_filter_placeholder": "Case-insensitive substring match",
            "checkpoint_filter_tooltip": "Optional filter pattern (case-insensitive substring)",
            "select_models_placeholder": "Nomes separados por virgula (ex: a.safetensors, b.safetensors)",
            "select_models_tooltip": "Selecione modelos especificos para girar entre eles. "
                                     "Exemplo: 'krea2Softrealism_v10, krea2WRC8_3210425'",
        },
        "en": {
            "model_folder_label": "Model category:",
            "model_folder_tooltip": "checkpoints = with embedded CLIP/VAE\n diffusion_models/unet = no embedded CLIP (requires separate CLIPLoader/VAELoader)",
            "checkpoint_filter_label": "Filter by name:",
            "info_title": "Rotation info:",
            "subfolder_placeholder": "subfolder path (leave empty for root)",
            "change_interval_tooltip": "Number of images before switching model",
            "batch_index_tooltip": "Current batch index (use BatchIndexCounter)",
            "rotation_mode_tooltip": "How to select next model",
            "seed_tooltip": "Seed for random/shuffle modes",
            "checkpoint_filter_placeholder": "Case-insensitive substring match",
            "checkpoint_filter_tooltip": "Optional filter pattern (case-insensitive substring)",
            "select_models_placeholder": "Comma-separated names (ex: a.safetensors, b.safetensors)",
            "select_models_tooltip": "Pick specific models to rotate between. "
                                     "Example: 'krea2Softrealism_v10, krea2WRC8_3210425'",
        },
        "zh": {
            "model_folder_label": "模型类别:",
            "model_folder_tooltip": "checkpoints = 内置CLIP/VAE\n diffusion_models/unet = 无内置CLIP (需要单独的CLIPLoader/VAELoader)",
            "checkpoint_filter_label": "按名称过滤:",
            "info_title": "轮换信息:",
            "subfolder_placeholder": "留空以使用根目录的子文件夹",
            "change_interval_tooltip": "在切换模型前生成的图像数量",
            "batch_index_tooltip": "当前批次索引 (使用 BatchIndexCounter)",
            "rotation_mode_tooltip": "如何选择下一个模型",
            "seed_tooltip": "随机/洗牌模式的种子",
            "checkpoint_filter_placeholder": "不区分大小写的子字符串匹配",
            "checkpoint_filter_tooltip": "可选的过滤模式（不区分大小写的子字符串）",
            "select_models_placeholder": "逗号分隔的名称（例：a.safetensors, b.safetensors）",
            "select_models_tooltip": "选择要轮换的特定模型。示例：'krea2Softrealism_v10, krea2WRC8_3210425'",
        },
    },
    # ── Node: Simple Checkpoint Rotation ───────────────────────────────────
    "simple_rotation": {
        "pt": {
            "subfolder_label": "Subpasta:",
            "change_every_label": "Mudar a cada N imagens:",
            "auto_increment_label": "Incremento automático:",
            "manual_index_label": "Índice manual:",
        },
        "en": {
            "subfolder_label": "Subfolder:",
            "change_every_label": "Change every N images:",
            "auto_increment_label": "Auto-increment:",
            "manual_index_label": "Manual index:",
        },
        "zh": {
            "subfolder_label": "子文件夹:",
            "change_every_label": "每N张图换一次:",
            "auto_increment_label": "自动递增:",
            "manual_index_label": "手动索引:",
        },
    },
    # ── Node: Checkpoint Rotation With Counter ─────────────────────────────
    "rotation_with_counter": {
        "pt": {
            "counter_label": "Contador:",
            "subfolder_label": "Subpasta:",
            "change_every_label": "Mudar a cada N imagens:",
            "reset_on_next_label": "Resetar no próximo:",
        },
        "en": {
            "counter_label": "Counter:",
            "subfolder_label": "Subfolder:",
            "change_every_label": "Change every N images:",
            "reset_on_next_label": "Reset on next:",
        },
        "zh": {
            "counter_label": "计数器:",
            "subfolder_label": "子文件夹:",
            "change_every_label": "每N张图换一次:",
            "reset_on_next_label": "在下一次重置:",
        },
    },
    # ── Node: Checkpoint Rotation Simple (direct) ──────────────────────────
    "rotation_simple_direct": {
        "pt": {
            "checkpoint_index_label": "Índice do checkpoint:",
            "subfolder_label": "Subpasta:",
            "change_every_label": "Mudar a cada N imagens:",
        },
        "en": {
            "checkpoint_index_label": "Checkpoint index:",
            "subfolder_label": "Subfolder:",
            "change_every_label": "Change every N images:",
        },
        "zh": {
            "checkpoint_index_label": "检查点索引:",
            "subfolder_label": "子文件夹:",
            "change_every_label": "每N张图换一次:",
        },
    },
    # ── Node: Save Image (with Checkpoint Info) ────────────────────────────
    "save_with_checkpoint": {
        "pt": {
            "checkpoint_name_label": "Nome do modelo:",
            "filename_prefix_label": "Prefixo do arquivo:",
            "checkpoint_info_label": "Info do checkpoint:",
        },
        "en": {
            "checkpoint_name_label": "Model name:",
            "filename_prefix_label": "Filename prefix:",
            "checkpoint_info_label": "Checkpoint info:",
        },
        "zh": {
            "checkpoint_name_label": "模型名称:",
            "filename_prefix_label": "文件前缀:",
            "checkpoint_info_label": "检查点信息:",
        },
    },
    # ── Node: Add Checkpoint To Metadata ───────────────────────────────────
    "add_checkpoint_metadata": {
        "pt": {
            "checkpoint_name_label": "Nome do checkpoint:",
        },
        "en": {
            "checkpoint_name_label": "Checkpoint name:",
        },
        "zh": {
            "checkpoint_name_label": "检查点名称:",
        },
    },
    # ── Mensagens Gerais ───────────────────────────────────────────────────
    "general": {
        "pt": {
            "diffusion_models_help": "Modelos de difusão sem CLIP embutido. Use nós CLIPLoader e VAELoader separados na sua workflow.",
            "checkpoints_help": "Checklists padrão com CLIP e VAE embutidos. Funciona imediatamente.",
            "model_folder_changed": "Categoria alterada para: {category}",
        },
        "en": {
            "diffusion_models_help": " Diffusion models without embedded CLIP. Use separate CLIPLoader and VAELoader nodes in your workflow.",
            "checkpoints_help": "Default checklists with embedded CLIP and VAE. Works immediately.",
            "model_folder_changed": "Category changed to: {category}",
        },
        "zh": {
            "diffusion_models_help": " 无嵌入式CLIP的扩散模型。在您的工作流程中单独使用CLIPLoader和VAELoader节点。",
            "checkpoints_help": "带有内置CLIP和VAE的标准检查点。即时工作。",
            "model_folder_changed": "更改类别到: {category}",
        },
    },
}


def load_language_config() -> None:
    """Carrega o idioma salvo do config.json, se existir.

    O arquivo deve ter a estrutura: {"language": "pt"}
    Se o arquivo não existir ou o idioma for inválido, usa o padrão 'pt' (ptbr).
    """
    global current_language
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            lang = data.get("language", DEFAULT_LANGUAGE)
            if lang in LANGUAGES:
                current_language = lang
                return
    except (json.JSONDecodeError, KeyError, TypeError, OSError):
        pass
    # Fallback para português (ptbr)
    current_language = DEFAULT_LANGUAGE


def save_language_config(language_code: str) -> None:
    """Salva a escolha de linguagem no config.json.

    Args:
        language_code: código do idioma ('pt', 'en' ou 'zh')
    """
    if language_code not in LANGUAGES:
        raise ValueError(f"Idioma inválido: {language_code}. Use pt, en ou zh.")
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"language": language_code}, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"[i18n] Não foi possível salvar o config: {e}")


def set_language(language_code: str) -> None:
    """Define o idioma atual para uso nos nodes.

    Também salva a escolha no config.json para persistência entre sessões.

    Args:
        language_code: código do idioma ('pt', 'en' ou 'zh')
    """
    global current_language
    if language_code not in LANGUAGES:
        raise ValueError(f"Idioma inválido: {language_code}. Use pt, en ou zh.")
    current_language = language_code
    save_language_config(language_code)


def get(key: str, node: str, default=None):
    """Obter texto traduzido na linguagem corrente.

    Args:
        key: chave da tradução (ex: "model_folder_label")
        node: nome do node (ex: "checkpoint_rotation")
        default: valor padrão se não encontrar

    Returns:
        Texto na linguagem corrente ou o default
    """
    node_translations = TRANSLATIONS.get(node, {})
    return node_translations.get(current_language, {}).get(key, default)


def get_general(key: str, default=None):
    """Obter texto da categoria geral (ex: mensagens de ajuda)."""
    general = TRANSLATIONS.get("general", {})
    return general.get(current_language, {}).get(key, default)


def list_languages() -> Dict[str, str]:
    """Retorna dicionário de idiomas disponíveis {codigo: nome}."""
    return LANGUAGES.copy()


# Auto-carregar config na importação
load_language_config()

# Expor para uso direto nos templates/nodes
__all__ = [
    "set_language",
    "get",
    "get_general",
    "list_languages",
    "current_language",
    "save_language_config",
    "load_language_config",
]