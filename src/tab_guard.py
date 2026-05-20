import gc
import json

import streamlit as st

from src.subprocess_helpers import release_upload

# Keys in st.session_state that hold finished result data for each page. When
# the user leaves a page, that page's keys are popped to free memory. Keys
# marked in DOWNLOAD_KEYS represent the "this page has an unused download link"
# state used to drive the confirm-before-leaving popup.
PAGE_RESULT_KEYS = {
    "translate": [
        "translated_bytes",
        "translated_name",
        "translated_file_id",
        "translate_source_bytes",
        "translate_proofread_result",
    ],
    "proofread": ["proofread_result"],
    "shrink": [
        "shrunk_bytes",
        "shrunk_name",
        "shrunk_file_id",
        "shrunk_original_size",
        "shrunk_target_bytes",
    ],
    "format": [
        "formatted_bytes",
        "formatted_name",
        "formatted_file_id",
    ],
}

DOWNLOAD_KEYS = {
    "translated_bytes",
    "translate_proofread_result",
    "proofread_result",
    "shrunk_bytes",
    "formatted_bytes",
}

# Per-page file_uploader widget keys. On tab change these are released from
# both Streamlit's MemoryUploadedFileManager (which holds the upload bytes)
# and from st.session_state (which holds the UploadedFile that refcounts the
# same bytes). Both refs must drop before Python will reclaim the upload.
PAGE_UPLOADER_KEYS = {
    "translate": ["translate_uploader"],
    "proofread": ["proofread_target_uploader", "proofread_source_uploader"],
    "shrink": ["shrink_uploader"],
    "format": ["format_uploader"],
}


def has_finished_downloads():
    for key in DOWNLOAD_KEYS:
        if st.session_state.get(key) is not None:
            return True
    return False


def _pop_keys(keys):
    for key in keys:
        if key in st.session_state:
            st.session_state.pop(key)


def _release_uploader_keys(keys):
    for key in keys:
        val = st.session_state.get(key)
        if val is None:
            continue
        # file_uploader returns either a single UploadedFile or a list
        # (accept_multiple_files=True). Handle both.
        items = val if isinstance(val, list) else [val]
        for item in items:
            release_upload(item)
        st.session_state.pop(key, None)


def clear_stale_results(active_url_path, previous_url_path):
    # On tab change, drop result data and uploader widgets belonging to the
    # pages we just left so their (potentially multi-GB) buffers are reclaimed.
    st.session_state["_active_page"] = active_url_path
    if previous_url_path is None or previous_url_path == active_url_path:
        return
    
    for path, keys in PAGE_RESULT_KEYS.items():
        if path != active_url_path:
            _pop_keys(keys)
            _release_uploader_keys(PAGE_UPLOADER_KEYS.get(path, []))
    gc.collect()


def inject_nav_guard(has_pending, confirm_message):
    # The iframe's JS realm is torn down on every Streamlit rerun, so an event
    # listener installed from inside the iframe goes stale. Instead, we update
    # parent-window flags from inside the iframe, and inject the actual click
    # listener as a <script> element into the parent document on first use so
    # the handler lives in the parent's JS realm.
    payload = json.dumps({"pending": bool(has_pending), "message": confirm_message})
    st.iframe(
        f"""
        <script>
          (function() {{
            const cfg = {payload};
            const w = window.parent;
            w.__pendingDownloads = cfg.pending;
            w.__pendingNavMessage = cfg.message;
            if (w.__stNavGuardInstalled) return;
            w.__stNavGuardInstalled = true;
            const installer = w.document.createElement('script');
            installer.textContent = `
              (function() {{
                document.addEventListener('click', function(ev) {{
                  if (!window.__pendingDownloads) return;
                  const t = ev.target;
                  const link = t && t.closest && t.closest('[data-testid="stTopNavLink"]');
                  if (!link) return;
                  const ok = window.confirm(window.__pendingNavMessage);
                  if (!ok) {{
                    ev.preventDefault();
                    ev.stopImmediatePropagation();
                  }}
                }}, true);
              }})();
            `;
            w.document.head.appendChild(installer);
          }})();
        </script>
        """,
        height=1,
    )
