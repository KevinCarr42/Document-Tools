import json

import streamlit as st

# Header/banner colors that must follow the *Streamlit* theme the user picked
# (light / dark / system), not the OS theme. prefers-color-scheme reads the OS,
# which is why the header used to go white-on-white when the menu and the OS
# disagreed. These are applied via _build_theme_css() using st.context.theme.
_THEME_PALETTES = {
    "light": {
        "header_bg": "#FFFFFF",
        "header_border": "rgba(128, 128, 128, 0.15)",
        "header_fg": "#0F172A",
        "toggle_border": "rgba(128, 128, 128, 0.3)",
        "toggle_hover_bg": "rgba(0, 0, 0, 0.05)",
        "toggle_hover_border": "rgba(128, 128, 128, 0.5)",
    },
    "dark": {
        "header_bg": "#0B1220",
        "header_border": "rgba(255, 255, 255, 0.08)",
        "header_fg": "#F1F5F9",
        "toggle_border": "rgba(255, 255, 255, 0.2)",
        "toggle_hover_bg": "rgba(255, 255, 255, 0.08)",
        "toggle_hover_border": "rgba(255, 255, 255, 0.35)",
    },
}

_GLOBAL_CSS = """
<style>
  [data-testid="stFileUploader"] [data-testid="stBaseButton-borderlessIcon"] { display: none !important; }

  /* Hide the script-runner iframe used by inject_text_replacements. st.iframe
     requires height >= 1, so we hide its container to keep the layout flush. */
  [data-testid="stElementContainer"]:has(> iframe[srcdoc]) {
    display: none !important;
  }

  /* Tighten the gap between the fixed banner and the first page element. Default
     padding-top is 8rem (room for the toolbar Streamlit's auto-hides). We've
     moved the nav into the header, so we don't need that much space. */
  [data-testid="stMainBlockContainer"] {
    padding-top: 4rem !important;
  }

  /* Download link: blue text, underline on hover. */
  [data-testid="stDownloadButton"] button,
  [data-testid="stDownloadButton"] button p {
    color: #2563EB !important;
    text-decoration: none !important;
  }
  [data-testid="stDownloadButton"] button:hover,
  [data-testid="stDownloadButton"] button:hover p {
    color: #1D4ED8 !important;
    text-decoration: underline !important;
  }

  /* Fixed header — always-visible app title. Background, border and text colors
     are theme-dependent and injected by _build_theme_css() (driven by
     st.context.theme, not prefers-color-scheme). */

  /* ---- Top navigation hoisted into the banner ------------------------------
     Streamlit renders st.navigation(position="top") just below the header by
     default. Fix-positioning lifts it INTO the visible banner area. Sits to
     the right of the title, left of the hamburger. */
  [data-testid="stTopNavSection"] {
    position: fixed !important;
    top: 0;
    right: 4rem;
    height: 3.75rem;
    z-index: 999990;
    display: flex !important;
    align-items: center;
    gap: 1.75rem;
    background: transparent !important;
    padding: 0 !important;
    margin: 0 !important;
    border: none !important;
    overflow: visible !important;
    flex-wrap: nowrap !important;
    width: auto !important;
    max-width: none !important;
  }
  /* Force all tab containers + links visible. Streamlit's ResizeObserver still
     measures the (now-empty) original parent and hides tabs into a popover at
     >100% zoom; these rules veto that. */
  [data-testid="stTopNavLinkContainer"] {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    display: flex !important;
    visibility: visible !important;
  }
  [data-testid="stTopNavLink"] {
    display: inline-flex !important;
    visibility: visible !important;
  }
  /* Hide the overflow popover ("…" / expand-arrow) since we want all tabs visible. */
  [data-testid="stTopNavPopover"],
  [data-testid="stTopNavDropdownLink"] {
    display: none !important;
  }

  /* Inactive tabs: lighter weight, dimmed.
     Streamlit wraps the label in <span><div><p>; the inner span has an
     emotion-generated class with its own font-size that beats ours unless
     we cascade through descendants. */
  [data-testid="stTopNavLink"],
  [data-testid="stTopNavLink"] *,
  [data-testid="stTopNavLink"] p {
    font-size: 1.15rem !important;
    font-weight: 400 !important;
    text-decoration: none !important;
  }
  [data-testid="stTopNavLink"] {
    opacity: 0.55;
    transition: opacity 0.15s ease;
  }
  [data-testid="stTopNavLink"]:hover { opacity: 1; }

  /* Active tab: bold, slightly larger, full opacity. */
  [data-testid="stTopNavLink"][aria-current="page"],
  [data-testid="stTopNavLink"][aria-current="page"] *,
  [data-testid="stTopNavLink"][aria-current="page"] p {
    font-size: 1.35rem !important;
    font-weight: 700 !important;
  }
  [data-testid="stTopNavLink"][aria-current="page"] {
    opacity: 1;
  }

  /* Nav link text color is theme-dependent — see _build_theme_css(). */

  /* ---- Language toggle ----------------------------------------------------
     The button is rendered as the first thing in streamlit_app.py, preceded
     by a hidden anchor div. We hide the anchor's container, then fix-position
     the *next* element-container (which holds the button) into the banner. */
  [data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] .lang-toggle-anchor) {
    display: none !important;
  }
  [data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] .lang-toggle-anchor) + [data-testid="stElementContainer"] {
    position: fixed !important;
    top: 0;
    right: 11rem;
    height: 3.75rem;
    z-index: 999991;
    display: flex !important;
    align-items: center;
    width: auto !important;
    max-width: none !important;
    margin: 0 !important;
    padding: 0 !important;
  }
  /* Style the actual button: subtle, blends into the banner. Text color and
     border/hover colors are theme-dependent — see _build_theme_css(). */
  [data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] .lang-toggle-anchor) + [data-testid="stElementContainer"] button {
    background: transparent !important;
    border: 1px solid rgba(128, 128, 128, 0.3) !important;
    font-size: 0.9rem !important;
    font-weight: 500 !important;
    padding: 0.35rem 0.85rem !important;
    border-radius: 0.375rem !important;
    transition: background-color 0.15s ease, border-color 0.15s ease;
  }

  /* Push the nav tabs further left to clear the lang toggle. Fixed position —
     no status-widget override, so nothing moves when scripts run. */
  [data-testid="stTopNavSection"] {
    right: 18rem !important;
  }
</style>
"""


def _build_theme_css(palette):
    return f"""
<style>
  /* Header banner — colors keyed to the Streamlit theme the user selected.
     The header is a sibling of .stApp so its theme vars don't resolve; we set
     explicit colors here instead. */
  header[data-testid="stHeader"] {{
    background-color: {palette["header_bg"]} !important;
    border-bottom: 1px solid {palette["header_border"]};
  }}
  header[data-testid="stHeader"]::before {{
    color: {palette["header_fg"]};
  }}
  /* All native header content — hamburger, "Running…" status text, spinner
     icons (SVGs use fill:currentColor) — plus the hoisted nav links. */
  header[data-testid="stHeader"] *,
  [data-testid="stTopNavLink"],
  [data-testid="stTopNavLink"] *,
  [data-testid="stTopNavLink"] p {{
    color: {palette["header_fg"]} !important;
  }}
  /* Language toggle button: theme-aware text, border and hover. */
  [data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] .lang-toggle-anchor) + [data-testid="stElementContainer"] button {{
    color: {palette["header_fg"]} !important;
    border-color: {palette["toggle_border"]} !important;
  }}
  [data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] .lang-toggle-anchor) + [data-testid="stElementContainer"] button:hover {{
    background-color: {palette["toggle_hover_bg"]} !important;
    border-color: {palette["toggle_hover_border"]} !important;
  }}
</style>
"""


def inject_global_styles():
    theme = getattr(st.context, "theme", None)
    theme_type = getattr(theme, "type", None)
    if theme_type not in _THEME_PALETTES:
        # st.context.theme can be None on the very first run before the frontend
        # reports it; fall back to the configured base ("dark").
        theme_type = "dark"
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)
    st.markdown(_build_theme_css(_THEME_PALETTES[theme_type]), unsafe_allow_html=True)


def inject_text_replacements(mapping: dict):
    """Translate hardcoded Streamlit widget strings (e.g. 'Drag and drop file here',
    'Browse files') by replacing their text nodes via JS. `mapping` is
    {found_text: replacement_text}.

    Runs in an iframe (st.iframe) because st.markdown sanitizes <script> tags.
    A MutationObserver on the parent document re-applies replacements whenever
    Streamlit re-renders DOM subtrees."""
    mapping_json = json.dumps(mapping or {})
    # height=1 (minimum st.iframe allows); the container is hidden via CSS in _GLOBAL_CSS.
    st.iframe(
        f"""
        <script>
          (function() {{
            const map = {mapping_json};
            const doc = window.parent.document;
            const w = window.parent;

            // Tear down any prior observer so they don't accumulate across reruns.
            if (w.__st_text_observer) w.__st_text_observer.disconnect();
            if (Object.keys(map).length === 0) return;

            const norm = (s) => s.replace(/\\s+/g, ' ').trim();
            const isLeafText = (el) => {{
              for (const c of el.childNodes) {{
                if (c.nodeType === Node.ELEMENT_NODE) return false;
              }}
              return true;
            }};

            function replace(root) {{
              // Pass 1: text-node walker (handles single-node strings: button labels etc.)
              const walker = doc.createTreeWalker(root, NodeFilter.SHOW_TEXT);
              let node;
              while ((node = walker.nextNode())) {{
                const t = norm(node.textContent);
                if (map[t]) {{
                  node.textContent = map[t];
                }}
              }}
              // Pass 2: element walker for leaf elements (handles strings split across
              // multiple text nodes inside one element, e.g. "200MB per file • DOCX"
              // which lives across two text nodes inside a single <span>).
              if (root.nodeType !== Node.ELEMENT_NODE) return;
              const elements = root.querySelectorAll('*');
              for (const el of elements) {{
                if (!isLeafText(el)) continue;
                const t = norm(el.textContent);
                if (map[t]) {{
                  el.textContent = map[t];
                }}
              }}
              if (isLeafText(root)) {{
                const t = norm(root.textContent);
                if (map[t]) {{
                  root.textContent = map[t];
                }}
              }}
            }}
            replace(doc.body);

            const obs = new MutationObserver((mutations) => {{
              for (const m of mutations) {{
                for (const n of m.addedNodes) {{
                  if (n.nodeType === Node.ELEMENT_NODE) replace(n);
                  else if (n.nodeType === Node.TEXT_NODE) {{
                    const t = n.textContent.trim();
                    if (map[t]) n.textContent = n.textContent.replace(t, map[t]);
                  }}
                }}
              }}
            }});
            obs.observe(doc.body, {{ childList: true, subtree: true }});
            w.__st_text_observer = obs;
          }})();
        </script>
        """,
        height=1,
    )
