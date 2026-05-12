import streamlit as st

TRANSLATIONS = {
    "en": {
        "tab.translate": "Translate Document",
        "tab.shrink": "Shrink Document",
        "tab.format": "Format Document",

        "translate.caption": "Upload a .docx file. It will be shrunk to ≤10 MB if needed, then translated between English and French.",
        "translate.uploader": "Upload Document to Translate",
        "translate.direction_en": "English → French",
        "translate.direction_fr": "French → English",
        "translate.button": "Translate",
        "translate.spinner": "Translating…",
        "translate.complete": "Translation complete.",
        "translate.shrink_info": "File exceeds the 10 MB Azure limit. Shrinking before translation…",
        "translate.shrink_spinner": "Shrinking embedded images…",
        "translate.shrink_done": "Shrunk: {before} → {after}",
        "translate.too_big": "Even after shrinking the file is {size}, still over the 10 MB limit. This document likely has very little compressible image content. Translation is not supported yet (would require the async batch client).",
        "translate.shrinker_failed": "Shrinker failed: {error}",
        "translate.azure_error": "Azure translation error: {error}",

        "shrink.caption": "Upload a .docx file and shrink it by re-encoding embedded images to fit a target size.",
        "shrink.uploader": "Upload Document to Shrink",
        "shrink.target_label": "Target size (MB)",
        "shrink.button": "Shrink",
        "shrink.spinner": "Shrinking embedded images…",
        "shrink.complete": "Shrunk: {before} → {after}",
        "shrink.failed": "Shrinker failed: {error}",

        "format.coming_soon": "Coming soon...",

        "common.download": "Download Link: {filename}",
        "uploader.dropzone": "Drag and drop file here",
        "uploader.browse": "Browse files",

        "lang.toggle_label": "Français",
    },
    "fr": {
        "tab.translate": "Traduire un document",
        "tab.shrink": "Réduire un document",
        "tab.format": "Mise en forme",

        "translate.caption": "Téléversez un fichier .docx. Il sera réduit à ≤10 Mo au besoin, puis traduit entre l'anglais et le français.",
        "translate.uploader": "Téléverser un document à traduire",
        "translate.direction_en": "Anglais → Français",
        "translate.direction_fr": "Français → Anglais",
        "translate.button": "Traduire",
        "translate.spinner": "Traduction en cours…",
        "translate.complete": "Traduction terminée.",
        "translate.shrink_info": "Le fichier dépasse la limite Azure de 10 Mo. Réduction avant traduction…",
        "translate.shrink_spinner": "Réduction des images intégrées…",
        "translate.shrink_done": "Réduit : {before} → {after}",
        "translate.too_big": "Après réduction, le fichier fait toujours {size}, au-delà de la limite de 10 Mo. Ce document contient probablement peu d'images compressibles. La traduction n'est pas encore prise en charge (nécessiterait le client de traduction par lots asynchrone).",
        "translate.shrinker_failed": "Échec de la réduction : {error}",
        "translate.azure_error": "Erreur de traduction Azure : {error}",

        "shrink.caption": "Téléversez un fichier .docx pour le réduire en ré-encodant les images intégrées jusqu'à la taille cible.",
        "shrink.uploader": "Téléverser un document à réduire",
        "shrink.target_label": "Taille cible (Mo)",
        "shrink.button": "Réduire",
        "shrink.spinner": "Réduction des images intégrées…",
        "shrink.complete": "Réduit : {before} → {after}",
        "shrink.failed": "Échec de la réduction : {error}",

        "format.coming_soon": "Bientôt disponible...",

        "common.download": "Lien de téléchargement : {filename}",
        "uploader.dropzone": "Glisser-déposer un fichier ici",
        "uploader.browse": "Parcourir les fichiers",

        "lang.toggle_label": "English",
    },
}


def get_lang():
    return st.session_state.get("lang", "en")


def t(key: str, **kwargs) -> str:
    """Translate a key into the active language. Missing keys fall back to EN, then to the raw key."""
    lang = get_lang()
    text: str = TRANSLATIONS.get(lang, {}).get(key) or TRANSLATIONS["en"].get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text


def toggle_lang():
    st.session_state.lang = "fr" if get_lang() == "en" else "en"


# Hardcoded Streamlit widget strings that don't accept a label argument
# (file_uploader's dropzone, the Browse button, etc.). Replaced at runtime
# via JS in styles.inject_text_replacements.
WIDGET_TEXT_PAIRS = [
    # (english, french)
    ("Drag and drop file here", "Glisser-déposer un fichier ici"),
    ("Browse files", "Parcourir les fichiers"),
    ("Upload", "Téléverser"),
]


WIDGET_TEXT_OVERRIDES = {
    # Streamlit's default text → what we want it to say (per language).
    # Use this for strings where the EN default isn't what we want either —
    # WIDGET_TEXT_PAIRS only handles EN↔FR swaps of Streamlit's own text.
    "200MB per file • DOCX": {
        "en": "Drag a DOCX file (max 200 MB)",
        "fr": "Glissez un fichier DOCX (max 200 Mo)",
    },
}


def widget_text_map():
    """Returns {found_text: replacement_text} for the active language.
    Includes the reverse direction so switching languages cleans up stale text."""
    lang = get_lang()
    mapping = {}

    # EN↔FR swaps of Streamlit's own English defaults
    if lang == "fr":
        mapping.update({en: fr for en, fr in WIDGET_TEXT_PAIRS})
    else:
        mapping.update({fr: en for en, fr in WIDGET_TEXT_PAIRS})

    # Overrides: replace Streamlit's default with our custom text in both modes
    for default_text, by_lang in WIDGET_TEXT_OVERRIDES.items():
        mapping[default_text] = by_lang[lang]
        # If user toggled languages, also map the previous override back so it updates
        other_lang = "en" if lang == "fr" else "fr"
        mapping[by_lang[other_lang]] = by_lang[lang]

    return mapping
