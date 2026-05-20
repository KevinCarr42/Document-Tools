from pathlib import Path

import streamlit as st
from azure.core.exceptions import HttpResponseError

from src.helpers import (
    SYNC_DOCUMENT_TRANSLATION_MAX_BYTES,
    translate_document_bytes,
)
from src.i18n import t
from src.proofreader import DEFAULT_MAX_ITERATIONS
from src.subprocess_helpers import run_proofread, run_shrink
from src.utils import mb

MAX_BYTES = SYNC_DOCUMENT_TRANSLATION_MAX_BYTES


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
    key="translate_uploader",
)

if "translated_bytes" not in st.session_state:
    st.session_state.translated_bytes = None
    st.session_state.translated_name = None
    st.session_state.translated_file_id = None
    st.session_state.translate_source_bytes = None
    st.session_state.translate_proofread_result = None

if uploaded is not None and st.session_state.translated_file_id != uploaded.file_id:
    st.session_state.translated_bytes = None
    st.session_state.translated_name = None
    st.session_state.translated_file_id = None
    st.session_state.translate_source_bytes = None
    st.session_state.translate_proofread_result = None

if uploaded is not None:
    original_size = uploaded.size
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
        ready_bytes = None
        ready = True

        if max_reduction or needs_shrink:
            with st.spinner(t("translate.shrink_spinner")):
                try:
                    if max_reduction:
                        shrunk = run_shrink(uploaded, uploaded.name, target_bytes=MAX_BYTES, extreme_only=True)
                    else:
                        shrunk = run_shrink(uploaded, uploaded.name, target_bytes=MAX_BYTES, maintain_image_quality=False)
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
        else:
            ready_bytes = uploaded.getvalue()
        
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
                stem = Path(uploaded.name).stem
                st.session_state.translated_bytes = translated
                st.session_state.translated_name = f"{stem}_translated.docx"
                st.session_state.translated_file_id = uploaded.file_id
                st.session_state.translate_source_bytes = ready_bytes
                st.session_state.translate_proofread_result = None
                st.session_state.pop("translate_uploader", None)
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
    
    proofread_result = st.session_state.translate_proofread_result
    if proofread_result is None:
        st.markdown(f"**{t('translate.proofread_prompt')}**")
        proofread_iterations = st.number_input(
            t("proofread.max_iterations_label"),
            min_value=1,
            max_value=10,
            value=DEFAULT_MAX_ITERATIONS,
            step=1,
            key="translate_proofread_iterations",
        )
        if st.button(t("proofread.button"), type="secondary", key="translate_proofread_btn"):
            progress = st.progress(0.0, text=t("proofread.spinner"))
            
            
            def _on_chunk(done, total):
                progress.progress(done / total, text=t("proofread.progress", done=done, total=total))
            
            
            with st.spinner(t("proofread.spinner")):
                try:
                    proofread_docx, proofread_changes = run_proofread(
                        target_source=st.session_state.translated_bytes,
                        source_source=st.session_state.translate_source_bytes,
                        target_filename=st.session_state.translated_name,
                        max_iterations=int(proofread_iterations),
                        progress_callback=_on_chunk,
                    )
                except ValueError as e:
                    msg = str(e)
                    if "too large" in msg.lower():
                        st.error(t("proofread.too_large"))
                    else:
                        st.error(t("proofread.error", error=msg))
                    proofread_docx = None
                    proofread_changes = None
                except Exception as e:
                    st.error(t("proofread.error", error=str(e)))
                    proofread_docx = None
                    proofread_changes = None
            progress.empty()
            
            if proofread_docx is not None:
                stem = Path(st.session_state.translated_name).stem
                st.session_state.translate_proofread_result = {
                    "docx_bytes": proofread_docx,
                    "changes_text": proofread_changes,
                    "docx_name": f"{stem}_proofread.docx",
                    "changes_name": f"{stem}_changes.txt",
                }
                st.rerun()
    else:
        st.success(t("proofread.complete"))
        if "Warnings" in proofread_result["changes_text"]:
            st.warning(t("proofread.skipped_warnings"))
        elif proofread_result["changes_text"].strip() == "No changes.":
            st.info(t("proofread.no_changes"))
        
        st.download_button(
            label=t("proofread.download_docx", filename=proofread_result["docx_name"]),
            data=proofread_result["docx_bytes"],
            file_name=proofread_result["docx_name"],
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            type="tertiary",
            key="translate_proofread_download_docx",
        )
        st.download_button(
            label=t("proofread.download_changes", filename=proofread_result["changes_name"]),
            data=proofread_result["changes_text"].encode("utf-8"),
            file_name=proofread_result["changes_name"],
            mime="text/plain",
            type="tertiary",
            key="translate_proofread_download_changes",
        )
