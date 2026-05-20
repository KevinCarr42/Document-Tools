from pathlib import Path

import streamlit as st

from src.i18n import t
from src.subprocess_helpers import run_shrink
from src.utils import mb

st.caption(t("shrink.caption"))

target_mb = st.number_input(
    t("shrink.target_label"),
    min_value=1,
    max_value=100,
    value=10,
    step=1,
)

uploaded = st.file_uploader(
    t("shrink.uploader"),
    type=["docx"],
    label_visibility="collapsed",
    key="shrink_uploader",
)

if "shrunk_bytes" not in st.session_state:
    st.session_state.shrunk_bytes = None
    st.session_state.shrunk_name = None
    st.session_state.shrunk_file_id = None
    st.session_state.shrunk_original_size = None
    st.session_state.shrunk_target_bytes = None

if uploaded is not None and st.session_state.shrunk_file_id != uploaded.file_id:
    st.session_state.shrunk_bytes = None
    st.session_state.shrunk_name = None
    st.session_state.shrunk_file_id = None
    st.session_state.shrunk_original_size = None
    st.session_state.shrunk_target_bytes = None

if uploaded is not None:
    original_size = uploaded.size
    st.write(f"**{uploaded.name}** — {mb(original_size)}")
    
    if st.session_state.shrunk_bytes is None:
        col_btn, col_toggle = st.columns([1, 3], vertical_alignment="center")
        with col_btn:
            shrink_clicked = st.button(t("shrink.button"), type="primary")
        with col_toggle:
            maintain_quality = st.checkbox(t("shrink.maintain_quality"), value=True)
    else:
        shrink_clicked = False
        maintain_quality = True
    
    if shrink_clicked:
        target_bytes = int(target_mb) * 1024 * 1024
        with st.spinner(t("shrink.spinner")):
            try:
                shrunk = run_shrink(
                    uploaded,
                    uploaded.name,
                    target_bytes=target_bytes,
                    maintain_image_quality=maintain_quality,
                )
            except Exception as e:
                st.error(t("shrink.failed", error=str(e)))
                shrunk = None
        
        if shrunk is not None:
            stem = Path(uploaded.name).stem
            st.session_state.shrunk_bytes = shrunk
            st.session_state.shrunk_name = f"{stem}_shrunk.docx"
            st.session_state.shrunk_file_id = uploaded.file_id
            st.session_state.shrunk_original_size = original_size
            st.session_state.shrunk_target_bytes = target_bytes
            st.session_state.pop("shrink_uploader", None)
            st.rerun()

if st.session_state.shrunk_bytes is not None:
    new_size = len(st.session_state.shrunk_bytes)
    target = st.session_state.shrunk_target_bytes
    if target is not None and new_size > target:
        st.error(t("shrink.over_target", before=mb(st.session_state.shrunk_original_size), after=mb(new_size)))
    else:
        st.success(t("shrink.complete", before=mb(st.session_state.shrunk_original_size), after=mb(new_size)))
    st.download_button(
        label=t("common.download", filename=st.session_state.shrunk_name),
        data=st.session_state.shrunk_bytes,
        file_name=st.session_state.shrunk_name,
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        type="tertiary",
    )
