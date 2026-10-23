"""
Test for the i18n module.

Verifies:
- Default language is pt-BR
- All three languages are available
- Translations resolve for each language
- The config file round-trips (save then load)
- An invalid language raises
"""

import json
import os

import pytest

from utils import i18n


def test_default_language_is_ptbr():
    """The project must ship with ptbr as the default."""
    assert i18n.DEFAULT_LANGUAGE == "pt"
    assert i18n.LANGUAGES["pt"] == "Português (ptbr)"


def test_all_languages_available():
    """pt, en and zh must be registered."""
    langs = i18n.list_languages()
    assert set(langs.keys()) == {"pt", "en", "zh"}
    assert "Português" in langs["pt"]
    assert langs["en"] == "English"
    assert "中文" in langs["zh"]


def test_translations_resolve_per_language():
    """Each language must return its own text for the same key."""
    i18n.set_language("pt")
    pt_label = i18n.get("model_folder_label", "checkpoint_rotation")
    assert pt_label == "Categoria de modelo:"

    i18n.set_language("en")
    en_label = i18n.get("model_folder_label", "checkpoint_rotation")
    assert en_label == "Model category:"

    i18n.set_language("zh")
    zh_label = i18n.get("model_folder_label", "checkpoint_rotation")
    assert zh_label == "模型类别:"

    # Restore the default
    i18n.set_language("pt")


def test_general_help_translations():
    """The diffusion/checkpoints help texts must exist in every language."""
    for lang in ("pt", "en", "zh"):
        i18n.set_language(lang)
        assert i18n.get_general("diffusion_models_help"), f"missing diffusion help for {lang}"
        assert i18n.get_general("checkpoints_help"), f"missing checkpoints help for {lang}"
    i18n.set_language("pt")


def test_select_models_translations():
    """The select_models field must have a translated placeholder in every language."""
    for lang in ("pt", "en", "zh"):
        i18n.set_language(lang)
        assert i18n.get("select_models_placeholder", "checkpoint_rotation"), \
            f"missing select_models placeholder for {lang}"
    i18n.set_language("pt")


def test_invalid_language_raises():
    """An unknown language code must be rejected."""
    with pytest.raises(ValueError):
        i18n.set_language("fr")


def test_config_round_trip(tmp_path, monkeypatch):
    """Saving then loading the config must restore the language."""
    cfg = tmp_path / "language_config.json"
    monkeypatch.setattr(i18n, "CONFIG_PATH", str(cfg))

    i18n.set_language("en")
    assert cfg.exists(), "config file should have been written"
    with open(cfg, encoding="utf-8") as fh:
        data = json.load(fh)
    assert data["language"] == "en"

    # Simulate a fresh session
    i18n.load_language_config()
    assert i18n.current_language == "en"

    # Unknown language in the config falls back to the default
    with open(cfg, "w", encoding="utf-8") as fh:
        json.dump({"language": "klingon"}, fh)
    i18n.load_language_config()
    assert i18n.current_language == "pt"


def test_missing_config_falls_back_to_default(tmp_path, monkeypatch):
    """No config file → ptbr."""
    monkeypatch.setattr(i18n, "CONFIG_PATH", str(tmp_path / "does_not_exist.json"))
    i18n.load_language_config()
    assert i18n.current_language == "pt"
