import logging
import os

import streamlit as st
from dotenv import load_dotenv

from src.i18n import t, widget_text_map
from src.styles import inject_global_styles, inject_text_replacements

load_dotenv(override=True)
_dev_mode = os.environ.get("DEV_MODE", "").strip().lower() in ("1", "true", "yes", "on")
_app_logger = logging.getLogger("doc_tools")
_app_logger.setLevel(logging.INFO if _dev_mode else logging.WARNING)
_app_logger.propagate = False
if not _app_logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(message)s"))
    _app_logger.addHandler(_handler)

st.set_page_config(page_title="SciTrans", page_icon=None)
inject_global_styles()
inject_text_replacements(widget_text_map())

if "lang" not in st.session_state:
    st.session_state.lang = "en"

pages = [
    st.Page("pages/translate.py", title=t("tab.translate"), default=True, url_path="translate"),
    st.Page("pages/proofread.py", title=t("tab.proofread"), url_path="proofread"),
    st.Page("pages/shrink.py", title=t("tab.shrink"), url_path="shrink"),
    st.Page("pages/format.py", title=t("tab.format"), url_path="format"),
    st.Page("pages/settings.py", title=t("tab.settings"), url_path="settings"),
]
st.navigation(pages, position="top").run()
