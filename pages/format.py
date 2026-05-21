from pathlib import Path

import streamlit as st

from src.doc_formatter import format_document_bytes
from src.doc_localizer import localize_document_bytes
from src.i18n import t
from src.subprocess_helpers import run_shrink
from src.utils import mb

_REPORT_LINES = [
    ("smart_tags", "format.report_smart_tags"),
    ("proof_errors", "format.report_proof_errors"),
    ("orphan_fields", "format.report_orphan_fields"),
    ("manual_colours", "format.report_manual_colours"),
    ("blank_run_formatting", "format.report_blank_runs"),
    ("merged_runs", "format.report_merged_runs"),
]

_LOCALIZE_REPORT_LINES = [
    ("numbers", "format.report_localize_numbers"),
    ("percent", "format.report_localize_percent"),
    ("punctuation", "format.report_localize_punctuation"),
]


def _render_report(summary, localize_summary=None):
    locations = summary["locations"]
    lines = [
        t("format.report_title"),
        "",
        t("format.report_paragraphs", count=summary["paragraphs_scanned"]),
        t(
            "format.report_locations",
            body=locations["body"],
            tables=locations["tables"],
            hf=locations["headers_footers"],
        ),
        "",
    ]
    fixes = summary["fixes"]
    if any(fixes.values()):
        for key, message in _REPORT_LINES:
            lines.append(t(message, count=fixes[key]))
    else:
        lines.append(t("format.report_no_changes"))
    
    if localize_summary is not None:
        lines.append("")
        lines.append(t("format.report_localize_title"))
        lines.append(t("format.report_localize_nodes", count=localize_summary["text_nodes_scanned"]))
        localize_fixes = localize_summary["fixes"]
        if any(localize_fixes.values()):
            for key, message in _LOCALIZE_REPORT_LINES:
                lines.append(t(message, count=localize_fixes[key]))
        else:
            lines.append(t("format.report_localize_no_changes"))
    
    return "\n".join(lines) + "\n"


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

_LOCALIZE_LABELS = {
    "off": "format.localize_off",
    "en": "format.localize_en",
    "fr": "format.localize_fr",
}

localize_target = st.radio(
    t("format.localize_label"),
    options=["off", "en", "fr"],
    format_func=lambda choice: t(_LOCALIZE_LABELS[choice]),
    horizontal=True,
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
    st.session_state.formatted_summary = None
    st.session_state.formatted_localize_summary = None

if uploaded is not None and st.session_state.formatted_file_id != uploaded.file_id:
    st.session_state.formatted_bytes = None
    st.session_state.formatted_name = None
    st.session_state.formatted_file_id = None
    st.session_state.formatted_summary = None
    st.session_state.formatted_localize_summary = None

if uploaded is not None:
    st.write(f"**{uploaded.name}** — {mb(uploaded.size)}")
    
    if st.session_state.formatted_bytes is None and st.button(t("format.button"), type="primary"):
        cleaned = None
        summary = None
        localize_summary = None
        target_bytes = int(target_mb) * 1024 * 1024 if reduce_images else None
        with st.spinner(t("format.spinner")):
            try:
                document_bytes = run_shrink(uploaded, uploaded.name, target_bytes=target_bytes) if reduce_images else uploaded.getvalue()
                cleaned, summary = format_document_bytes(document_bytes)
                if localize_target != "off":
                    cleaned, localize_summary = localize_document_bytes(cleaned, localize_target)
            except Exception as e:
                st.error(t("format.failed", error=str(e)))
        
        if cleaned is not None:
            stem = Path(uploaded.name).stem
            st.session_state.formatted_bytes = cleaned
            st.session_state.formatted_name = f"{stem}_formatted.docx"
            st.session_state.formatted_file_id = uploaded.file_id
            st.session_state.formatted_summary = summary
            st.session_state.formatted_localize_summary = localize_summary
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
    if st.session_state.formatted_summary is not None:
        report_name = f"{Path(st.session_state.formatted_name).stem}_report.txt"
        st.download_button(
            label=t("format.download_summary", filename=report_name),
            data=_render_report(
                st.session_state.formatted_summary,
                st.session_state.formatted_localize_summary,
            ).encode("utf-8"),
            file_name=report_name,
            mime="text/plain",
            type="tertiary",
        )
