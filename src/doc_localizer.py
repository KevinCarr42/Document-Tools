import io
import logging
import re
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

logger = logging.getLogger("doc_tools.localizer")

_T = qn("w:t")
_DEL = qn("w:del")
_HDR = qn("w:hdr")
_FTR = qn("w:ftr")

NBSP = " "

# A number is only reformatted when it already carries a grouping separator or
# a decimal part. Bare integers (years, page numbers, counts) are left alone so
# "2024" never becomes "2 024".
_EN_NUMBER = re.compile(
    r"(?<![\d.,])(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+)(?![\d.,])"
)
_FR_NUMBER = re.compile(
    r"(?<![\d., ])(?:\d{1,3}(?: \d{3})+(?:,\d+)?|\d+,\d+)(?![\d.,])"
)

_PERCENT = re.compile(r"(\d)[  ]*(%)")

# French: a non-breaking space precedes : ; ? ! and sits inside guillemets.
# The colon rule skips URLs (://), clock times (10:30) and an existing NBSP.
_FRENCH_PUNCTUATION = [
    (re.compile(r"(?<![:/\d ]) ?(:)(?!/)"), NBSP + r"\1"),
    (re.compile(r"(?<! ) ?(;)"), NBSP + r"\1"),
    (re.compile(r"(?<! ) ?(\?)"), NBSP + r"\1"),
    (re.compile(r"(?<! ) ?(!)"), NBSP + r"\1"),
    (re.compile(r"«[  ]*"), "«" + NBSP),
    (re.compile(r"[  ]*»"), NBSP + "»"),
]

# English: punctuation sits tight against the preceding word.
_ENGLISH_PUNCTUATION = [
    (re.compile(r"[  ]+([:;?!])"), r"\1"),
]


def _en_number_to_fr(match):
    # 1,234.5 → 1 234,5: comma groups become NBSP, then the decimal point
    # becomes a comma. Order matters — grouping first, so the new decimal
    # comma is not itself swapped to NBSP.
    return match.group(0).replace(",", NBSP).replace(".", ",")


def _fr_number_to_en(match):
    # 1 234,5 → 1,234.5: the decimal comma becomes a point first, so the
    # NBSP→comma step cannot reintroduce a stray decimal comma.
    return match.group(0).replace(",", ".").replace(NBSP, ",")


_RULES = {
    "fr": (
            [("numbers", _EN_NUMBER, _en_number_to_fr)]
            + [("percent", _PERCENT, r"\1" + NBSP + r"\2")]
            + [("punctuation", pattern, replacement) for pattern, replacement in _FRENCH_PUNCTUATION]
    ),
    "en": (
            [("numbers", _FR_NUMBER, _fr_number_to_en)]
            + [("percent", _PERCENT, r"\1\2")]
            + [("punctuation", pattern, replacement) for pattern, replacement in _ENGLISH_PUNCTUATION]
    ),
}

_FIX_KEYS = ("numbers", "percent", "punctuation")

# Labels for the English change report, in report order.
_FIX_LABELS = (
    ("numbers", "Numbers reformatted"),
    ("percent", "Percent signs respaced"),
    ("punctuation", "Punctuation spacing fixed"),
)


def _apply(text, pattern, replacement):
    # Substitute, counting only matches that actually change the text so the
    # summary reflects real fixes rather than idempotent re-matches.
    changes = 0
    
    def _replace(match):
        nonlocal changes
        new = replacement(match) if callable(replacement) else match.expand(replacement)
        if new != match.group(0):
            changes += 1
        return new
    
    return pattern.sub(_replace, text), changes


def localize_text(text, target_lang):
    if target_lang not in _RULES:
        raise ValueError(f"target_lang must be 'en' or 'fr', got {target_lang!r}")
    counts = {key: 0 for key in _FIX_KEYS}
    for key, pattern, replacement in _RULES[target_lang]:
        text, changes = _apply(text, pattern, replacement)
        counts[key] += changes
    return text, counts


def localize_document_bytes(docx_bytes, target_lang):
    if target_lang not in _RULES:
        raise ValueError(f"target_lang must be 'en' or 'fr', got {target_lang!r}")
    doc = Document(io.BytesIO(docx_bytes))
    
    summary = {
        "text_nodes_scanned": 0,
        "fixes": {key: 0 for key in _FIX_KEYS},
    }
    
    for root in _iter_story_roots(doc):
        for text_node in root.iter(_T):
            original = text_node.text or ""
            if not original or _in_deletion(text_node):
                continue
            summary["text_nodes_scanned"] += 1
            localized, counts = localize_text(original, target_lang)
            if localized == original:
                continue
            text_node.text = localized
            text_node.set(qn("xml:space"), "preserve")
            for key, value in counts.items():
                summary["fixes"][key] += value
    
    logger.info(
        f"[localizer] target {target_lang} | "
        f"scanned {summary['text_nodes_scanned']} text nodes | "
        + " | ".join(f"{key} {count}" for key, count in summary["fixes"].items())
    )
    
    output = io.BytesIO()
    doc.save(output)
    return output.getvalue(), summary


def localize_document(file_path, target_lang):
    path = Path(file_path)
    localized, summary = localize_document_bytes(path.read_bytes(), target_lang)
    output_path = path.with_stem(f"{path.stem}_localized")
    output_path.write_bytes(localized)
    report_path = output_path.with_name(f"{output_path.stem}_report.txt")
    report_path.write_text(_render_summary(summary, target_lang), encoding="utf-8")
    return output_path


def _iter_story_roots(doc):
    # The body plus every header/footer part — the same stories doc_formatter
    # scans, so localization reaches running heads and page footers.
    yield doc.element.body
    for part in doc.part.package.parts:
        element = getattr(part, "element", None)
        if element is not None and element.tag in (_HDR, _FTR):
            yield element


def _in_deletion(node):
    # Text inside a tracked-change <w:del> is already struck out; rewriting it
    # would resurrect deleted content.
    for _ in node.iterancestors(_DEL):
        return True
    return False


def _render_summary(summary, target_lang):
    lines = [
        "Localization summary",
        "",
        f"Target language: {target_lang}",
        f"Text segments scanned: {summary['text_nodes_scanned']}",
        "",
    ]
    fixes = summary["fixes"]
    if any(fixes.values()):
        for key, label in _FIX_LABELS:
            lines.append(f"{label}: {fixes[key]}")
    else:
        lines.append("No localization changes were needed.")
    return "\n".join(lines) + "\n"
