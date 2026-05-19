import streamlit as st

from src.i18n import t, toggle_lang

st.markdown(f"### {t('settings.lang')}")

if st.button(t("lang.toggle_label"), key="lang_toggle"):
    toggle_lang()
    st.rerun()

st.markdown(f"### {t('settings.lexical_constraints')}")
st.markdown(f"\t{t('general.coming_soon')}")

st.markdown(f"### {t('settings.proofreader_prompts')}")
st.markdown(f"\t{t('general.coming_soon')}")
