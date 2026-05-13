import tempfile
from pathlib import Path

import streamlit as st
from azure.core.exceptions import HttpResponseError

from i18n import t
from src.doc_shrinker import compress_docx_images
from src.helpers import (
    SYNC_DOCUMENT_TRANSLATION_MAX_BYTES,
    translate_document_bytes,
)
from utils import mb

MAX_BYTES = SYNC_DOCUMENT_TRANSLATION_MAX_BYTES


def shrink_to_target(data, original_name, maintain_image_quality=True, extreme_only=False):
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp) / original_name
        tmp_path.write_bytes(data)
        out_path = compress_docx_images(
            tmp_path,
            target_bytes=MAX_BYTES,
            maintain_image_quality=maintain_image_quality,
            extreme_only=extreme_only,
        )
        return out_path.read_bytes()


st.caption(t("translate.caption"))

source_language = st.radio(
    "Translation Language",
    options=["en", "fr"],
    format_func=lambda code: t(f"translate.direction_{code}"),
    horizontal=True,
    label_visibility="collapsed",
)

uploaded = st.file_uploader(
    t("translate.uploader"),
    type=["docx"],
    label_visibility="collapsed",
)

if "translated_bytes" not in st.session_state:
    st.session_state.translated_bytes = None
    st.session_state.translated_name = None
    st.session_state.translated_file_id = None

if uploaded is not None and st.session_state.translated_file_id != uploaded.file_id:
    st.session_state.translated_bytes = None
    st.session_state.translated_name = None
    st.session_state.translated_file_id = None

if uploaded is not None:
    raw = uploaded.getvalue()
    original_size = len(raw)
    st.write(f"**{uploaded.name}** — {mb(original_size)}")
    
    max_reduction = st.checkbox(
        t("translate.max_reduction"),
        value=False,
        help=t("translate.max_reduction_help"),
        disabled=st.session_state.translated_bytes is not None,
    )
    
    needs_shrink = original_size > MAX_BYTES
    if needs_shrink:
        st.info(t("translate.shrink_info"))
    
    if st.session_state.translated_bytes is None and st.button(t("translate.button"), type="primary"):
        ready_bytes = raw
        ready = True
        
        if max_reduction or needs_shrink:
            with st.spinner(t("translate.shrink_spinner")):
                try:
                    if max_reduction:
                        shrunk = shrink_to_target(raw, uploaded.name, extreme_only=True)
                    else:
                        shrunk = shrink_to_target(raw, uploaded.name, maintain_image_quality=False)
                except Exception as e:
                    st.error(t("translate.shrinker_failed", error=str(e)))
                    ready = False
                    shrunk = None
            
            if shrunk is not None:
                new_size = len(shrunk)
                st.info(t("translate.shrink_done", before=mb(original_size), after=mb(new_size)))
                if new_size > MAX_BYTES:
                    st.error(t("translate.too_big", size=mb(new_size)))
                    ready = False
                else:
                    ready_bytes = shrunk
        
        if ready:
            with st.spinner(t("translate.spinner")):
                try:
                    translated = translate_document_bytes(
                        ready_bytes,
                        source_language=source_language,
                        filename=uploaded.name,
                    )
                except NotImplementedError as e:
                    st.error(str(e))
                    translated = None
                except ValueError as e:
                    st.error(str(e))
                    translated = None
                except HttpResponseError as e:
                    st.error(t("translate.azure_error", error=e.message))
                    translated = None
            
            if translated is not None:
                # TODO: proofreading pass
                stem = Path(uploaded.name).stem
                st.session_state.translated_bytes = translated
                st.session_state.translated_name = f"{stem}_translated.docx"
                st.session_state.translated_file_id = uploaded.file_id
                st.rerun()

if st.session_state.translated_bytes is not None:
    st.success(t("translate.complete"))
    st.download_button(
        label=t("common.download", filename=st.session_state.translated_name),
        data=st.session_state.translated_bytes,
        file_name=st.session_state.translated_name,
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        type="tertiary",
    )
