import streamlit as st

from i18n import t, toggle_lang, widget_text_map
from styles import inject_global_styles, inject_text_replacements

st.set_page_config(page_title="Document Tools", page_icon=None)
inject_global_styles()
inject_text_replacements(widget_text_map())

if "lang" not in st.session_state:
    st.session_state.lang = "en"

# Language toggle, right of the nav tabs.
st.markdown('<div class="lang-toggle-anchor"></div>', unsafe_allow_html=True)
if st.button(t("lang.toggle_label"), key="lang_toggle"):
    toggle_lang()
    st.rerun()

pages = [
    st.Page("pages/translate.py", title=t("tab.translate"), default=True, url_path="translate"),
    st.Page("pages/shrink.py", title=t("tab.shrink"), url_path="shrink"),
    st.Page("pages/format.py", title=t("tab.format"), url_path="format"),
]
st.navigation(pages, position="top").run()
