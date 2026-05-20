from pathlib import Path

import streamlit as st

from src.doc_formatter import format_document_bytes
from src.i18n import t
from src.subprocess_helpers import run_shrink
from src.utils import mb

st.caption(t("format.caption"))

reduce_images = st.toggle(t("format.reduce_images"), value=False)

if reduce_images:
    target_mb = st.number_input(
        t("shrink.target_label"),
        min_value=1,
        max_value=100,
        value=10,
        step=1,
    )

uploaded = st.file_uploader(
    t("format.uploader"),
    type=["docx"],
    label_visibility="collapsed",
    key="format_uploader",
)

if "formatted_bytes" not in st.session_state:
    st.session_state.formatted_bytes = None
    st.session_state.formatted_name = None
    st.session_state.formatted_file_id = None

if uploaded is not None and st.session_state.formatted_file_id != uploaded.file_id:
    st.session_state.formatted_bytes = None
    st.session_state.formatted_name = None
    st.session_state.formatted_file_id = None

if uploaded is not None:
    st.write(f"**{uploaded.name}** — {mb(uploaded.size)}")
    
    if st.session_state.formatted_bytes is None and st.button(t("format.button"), type="primary"):
        cleaned = None
        target_bytes = int(target_mb) * 1024 * 1024 if reduce_images else None
        with st.spinner(t("format.spinner")):
            try:
                document_bytes = run_shrink(uploaded, uploaded.name, target_bytes=target_bytes) if reduce_images else uploaded.getvalue()
                cleaned = format_document_bytes(document_bytes)
            except Exception as e:
                st.error(t("format.failed", error=str(e)))
        
        if cleaned is not None:
            stem = Path(uploaded.name).stem
            st.session_state.formatted_bytes = cleaned
            st.session_state.formatted_name = f"{stem}_formatted.docx"
            st.session_state.formatted_file_id = uploaded.file_id
            st.session_state.pop("format_uploader", None)
            st.rerun()

if st.session_state.formatted_bytes is not None:
    st.success(t("format.complete"))
    st.download_button(
        label=t("common.download", filename=st.session_state.formatted_name),
        data=st.session_state.formatted_bytes,
        file_name=st.session_state.formatted_name,
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        type="tertiary",
    )
