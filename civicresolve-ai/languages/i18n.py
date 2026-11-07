"""
CivicResolve AI - Multilingual Localization (i18n) Engine
Supports 6 languages: English (en), Arabic (ar), Hindi (hi), Urdu (ur), Malayalam (ml), Filipino (fil).
Provides automatic RTL layout injection for Arabic and Urdu.
"""
import os
import json
from typing import Dict, Any

LANG_DIR = os.path.dirname(os.path.abspath(__file__))

SUPPORTED_LANGUAGES = {
    "en": {"name": "English", "native": "English", "direction": "ltr"},
    "ar": {"name": "Arabic", "native": "العربية", "direction": "rtl"},
    "hi": {"name": "Hindi", "native": "हिन्दी", "direction": "ltr"},
    "ur": {"name": "Urdu", "native": "اردو", "direction": "rtl"},
    "ml": {"name": "Malayalam", "native": "മലയാളം", "direction": "ltr"},
    "fil": {"name": "Filipino", "native": "Filipino", "direction": "ltr"}
}

_LANG_CACHE: Dict[str, Dict[str, str]] = {}


def get_translations(lang_code: str = "en") -> Dict[str, str]:
    """Loads and caches translation dictionary for the selected language code."""
    code = lang_code.lower() if lang_code in SUPPORTED_LANGUAGES else "en"
    if code in _LANG_CACHE:
        return _LANG_CACHE[code]

    filepath = os.path.join(LANG_DIR, f"{code}.json")
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                _LANG_CACHE[code] = data
                return data
        except Exception:
            pass

    # Fallback to English
    en_path = os.path.join(LANG_DIR, "en.json")
    with open(en_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        _LANG_CACHE[code] = data
        return data


def t(key: str, lang_code: str = "en", default: str = "") -> str:
    """Translates a UI label key into the target language."""
    strings = get_translations(lang_code)
    return strings.get(key, default or key)


def is_rtl(lang_code: str) -> bool:
    """Returns True if the language uses Right-to-Left writing direction."""
    return SUPPORTED_LANGUAGES.get(lang_code, {}).get("direction") == "rtl"


def get_rtl_css(lang_code: str) -> str:
    """Returns CSS styles tailored for Arabic/Urdu RTL layout if active."""
    if not is_rtl(lang_code):
        return ""

    return """
    <style>
    /* CivicResolve AI RTL Layout Support for Arabic and Urdu */
    .stApp, div[data-testid="stChatMessageContent"], .stMarkdown, p, h1, h2, h3, h4, span, label {
        direction: rtl !important;
        text-align: right !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
    }
    div[data-testid="stSidebar"] {
        direction: rtl !important;
        text-align: right !important;
    }
    .stButton > button {
        direction: rtl !important;
    }
    input, textarea {
        direction: rtl !important;
        text-align: right !important;
    }
    </style>
    """
