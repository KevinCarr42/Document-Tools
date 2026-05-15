import streamlit as st

TRANSLATIONS = {
    "en": {
        "tab.translate": "Translate Document",
        "tab.shrink": "Shrink Document",
        "tab.proofread": "Proofread Translation",
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
        "translate.max_reduction": "Maximum image size reduction",
        "translate.max_reduction_help": "If you plan to replace images after translation, reducing image quality can make any unreplaced images more noticeable.",
        "translate.proofread_prompt": "Would you like to proofread this translation against the source?",
        
        "shrink.caption": "Upload a .docx file and shrink it by re-encoding embedded images to fit a target size.",
        "shrink.uploader": "Upload Document to Shrink",
        "shrink.target_label": "Target size (MB)",
        "shrink.button": "Shrink",
        "shrink.spinner": "Shrinking embedded images…",
        "shrink.complete": "Shrunk: {before} → {after}",
        "shrink.over_target": "Shrunk: {before} → {after} — final document size still exceeds target size",
        "shrink.failed": "Shrinker failed: {error}",
        "shrink.maintain_quality": "Maintain image quality",
        
        "proofread.caption": "Upload a translated .docx and (optionally) the source document. An LLM proofreads the translation, looping until no further changes are suggested.",
        "proofread.uploader_target": "Translated document (required)",
        "proofread.uploader_source": "Source document (optional — improves translation accuracy)",
        "proofread.max_iterations_label": "Maximum proofreading passes",
        "proofread.button": "Proofread",
        "proofread.spinner": "Proofreading…",
        "proofread.complete": "Proofreading complete.",
        "proofread.no_changes": "No changes were suggested.",
        "proofread.too_large": "Document too large for single-pass proofreading. Chunking is not yet supported.",
        "proofread.error": "Proofreading failed: {error}",
        "proofread.skipped_warnings": "Some paragraphs were skipped (hyperlinks, fields, or images). See the changes file.",
        "proofread.download_docx": "Download proofread .docx: {filename}",
        "proofread.download_changes": "Download change log: {filename}",
        
        "format.coming_soon": "Coming soon...",
        
        "common.download": "Download Link: {filename}",
        "uploader.dropzone": "Drag and drop file here",
        "uploader.browse": "Browse files",
        
        "lang.toggle_label": "Français",
    },
    "fr": {
        "tab.translate": "Traduire un document",
        "tab.shrink": "Réduire un document",
        "tab.proofread": "Réviser la traduction",
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
        "translate.max_reduction": "Réduction maximale de la taille des images",
        "translate.max_reduction_help": "Si vous prévoyez remplacer les images après la traduction, réduire la qualité des images peut rendre les images non remplacées plus visibles.",
        "translate.proofread_prompt": "Souhaitez-vous réviser cette traduction par rapport au document source ?",
        
        "shrink.caption": "Téléversez un fichier .docx pour le réduire en ré-encodant les images intégrées jusqu'à la taille cible.",
        "shrink.uploader": "Téléverser un document à réduire",
        "shrink.target_label": "Taille cible (Mo)",
        "shrink.button": "Réduire",
        "shrink.spinner": "Réduction des images intégrées…",
        "shrink.complete": "Réduit : {before} → {after}",
        "shrink.over_target": "Réduit : {before} → {after} — la taille finale du document dépasse encore la taille cible",
        "shrink.failed": "Échec de la réduction : {error}",
        "shrink.maintain_quality": "Conserver la qualité des images",
        
        "proofread.caption": "Téléversez un fichier .docx traduit et, au besoin, le document source. Un agent LLM révise la traduction et boucle jusqu'à ce qu'aucune autre correction ne soit proposée.",
        "proofread.uploader_target": "Document traduit (obligatoire)",
        "proofread.uploader_source": "Document source (optionnel — améliore la fidélité de la traduction)",
        "proofread.max_iterations_label": "Nombre maximal de passes de révision",
        "proofread.button": "Réviser",
        "proofread.spinner": "Révision en cours…",
        "proofread.complete": "Révision terminée.",
        "proofread.no_changes": "Aucune correction proposée.",
        "proofread.too_large": "Document trop volumineux pour une révision en une seule passe. Le découpage n'est pas encore pris en charge.",
        "proofread.error": "Échec de la révision : {error}",
        "proofread.skipped_warnings": "Certains paragraphes ont été ignorés (hyperliens, champs ou images). Voir le fichier des corrections.",
        "proofread.download_docx": "Télécharger le .docx révisé : {filename}",
        "proofread.download_changes": "Télécharger le journal des corrections : {filename}",
        
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
    lang = get_lang()
    mapping = {}
    
    if lang == "fr":
        mapping.update({en: fr for en, fr in WIDGET_TEXT_PAIRS})
    else:
        mapping.update({fr: en for en, fr in WIDGET_TEXT_PAIRS})
    
    for default_text, by_lang in WIDGET_TEXT_OVERRIDES.items():
        mapping[default_text] = by_lang[lang]
        other_lang = "en" if lang == "fr" else "fr"
        mapping[by_lang[other_lang]] = by_lang[lang]
    
    return mapping
