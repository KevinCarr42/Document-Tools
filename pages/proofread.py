import hashlib
from pathlib import Path

import streamlit as st

from src.i18n import t
from src.proofreader import DEFAULT_MAX_ITERATIONS, proofread_bytes
from src.utils import mb


def _dedupe_key(target_bytes, source_bytes):
    sha = hashlib.sha1()
    sha.update(target_bytes)
    if source_bytes is not None:
        sha.update(b"||")
        sha.update(source_bytes)
    return sha.hexdigest()[:16]


st.caption(t("proofread.caption"))

target = st.file_uploader(
    t("proofread.uploader_target"),
    type=["docx"],
    key="proofread_target_uploader",
)
source = st.file_uploader(
    t("proofread.uploader_source"),
    type=["docx"],
    key="proofread_source_uploader",
)

max_iterations = st.number_input(
    t("proofread.max_iterations_label"),
    min_value=1,
    max_value=10,
    value=DEFAULT_MAX_ITERATIONS,
    step=1,
)

if "proofread_result" not in st.session_state:
    st.session_state.proofread_result = None

if target is not None:
    target_bytes = target.getvalue()
    source_bytes = source.getvalue() if source is not None else None
    current_key = _dedupe_key(target_bytes, source_bytes)
    
    result = st.session_state.proofread_result
    if result is not None and result.get("dedupe_key") != current_key:
        st.session_state.proofread_result = None
        result = None
    
    st.write(f"**{target.name}** — {mb(len(target_bytes))}")
    if source is not None:
        st.write(f"**{source.name}** — {mb(len(source_bytes))}")
    
    if result is None and st.button(t("proofread.button"), type="primary"):
        progress = st.progress(0.0, text=t("proofread.spinner"))
        
        
        def _on_chunk(done, total):
            progress.progress(done / total, text=t("proofread.progress", done=done, total=total))
        
        
        with st.spinner(t("proofread.spinner")):
            try:
                docx_bytes, changes_text = proofread_bytes(
                    target_bytes=target_bytes,
                    source_bytes=source_bytes,
                    target_filename=target.name,
                    max_iterations=int(max_iterations),
                    progress_callback=_on_chunk,
                )
            except ValueError as e:
                msg = str(e)
                if "too large" in msg.lower():
                    st.error(t("proofread.too_large"))
                else:
                    st.error(t("proofread.error", error=msg))
                docx_bytes = None
                changes_text = None
            except Exception as e:
                st.error(t("proofread.error", error=str(e)))
                docx_bytes = None
                changes_text = None
        progress.empty()
        
        if docx_bytes is not None:
            stem = Path(target.name).stem
            st.session_state.proofread_result = {
                "docx_bytes": docx_bytes,
                "changes_text": changes_text,
                "docx_name": f"{stem}_proofread.docx",
                "changes_name": f"{stem}_changes.txt",
                "dedupe_key": current_key,
            }
            st.rerun()

if st.session_state.proofread_result is not None:
    result = st.session_state.proofread_result
    st.success(t("proofread.complete"))
    if "Warnings" in result["changes_text"]:
        st.warning(t("proofread.skipped_warnings"))
    elif result["changes_text"].strip() == "No changes.":
        st.info(t("proofread.no_changes"))
    
    st.download_button(
        label=t("proofread.download_docx", filename=result["docx_name"]),
        data=result["docx_bytes"],
        file_name=result["docx_name"],
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        type="tertiary",
    )
    st.download_button(
        label=t("proofread.download_changes", filename=result["changes_name"]),
        data=result["changes_text"].encode("utf-8"),
        file_name=result["changes_name"],
        mime="text/plain",
        type="tertiary",
    )
