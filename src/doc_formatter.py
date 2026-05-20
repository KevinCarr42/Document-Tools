import io
import logging
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

logger = logging.getLogger("doc_tools.formatter")

_P = qn("w:p")
_R = qn("w:r")
_RPR = qn("w:rPr")
_T = qn("w:t")
_TBL = qn("w:tbl")
_COLOR = qn("w:color")
_PROOF_ERR = qn("w:proofErr")
_HYPERLINK = qn("w:hyperlink")
_SMART_TAG = qn("w:smartTag")
_SMART_TAG_PR = qn("w:smartTagPr")
_FLD_CHAR = qn("w:fldChar")
_FLD_CHAR_TYPE = qn("w:fldCharType")
_HDR = qn("w:hdr")
_FTR = qn("w:ftr")

# Bold/italic/underline/superscript/subscript are the only run properties a
# paragraph is allowed to carry, and only on runs with visible text. On empty
# or whitespace-only runs they are stripped so the run can collapse to automatic.
_TEXT_ONLY_PROPERTIES = (
    qn("w:b"), qn("w:bCs"),
    qn("w:i"), qn("w:iCs"),
    qn("w:u"),
    qn("w:vertAlign"),
)

# Labels for the English change report, in report order.
_FIX_LABELS = (
    ("smart_tags", "Smart tags unwrapped"),
    ("proof_errors", "Stray proofing marks removed"),
    ("orphan_fields", "Orphaned field runs removed"),
    ("manual_colours", "Manual colours reset"),
    ("blank_run_formatting", "Blank-run formatting cleared"),
    ("merged_runs", "Disjointed runs merged"),
)


def format_document_bytes(docx_bytes):
    doc = Document(io.BytesIO(docx_bytes))
    
    summary = {
        "paragraphs_scanned": 0,
        "locations": {"body": 0, "tables": 0, "headers_footers": 0},
        "fixes": {key: 0 for key, _ in _PARAGRAPH_PASSES},
    }
    
    for root in _iter_story_roots(doc):
        for paragraph in root.iter(_P):
            summary["paragraphs_scanned"] += 1
            summary["locations"][_paragraph_location(root, paragraph)] += 1
            for key, count in _format_paragraph(paragraph).items():
                summary["fixes"][key] += count
    
    logger.info(
        f"[formatter] scanned {summary['paragraphs_scanned']} paragraphs | "
        + " | ".join(f"{key} {count}" for key, count in summary["fixes"].items())
    )
    
    output = io.BytesIO()
    doc.save(output)
    return output.getvalue(), summary


def format_document(file_path):
    path = Path(file_path)
    cleaned, summary = format_document_bytes(path.read_bytes())
    output_path = path.with_stem(f"{path.stem}_formatted")
    output_path.write_bytes(cleaned)
    report_path = output_path.with_name(f"{output_path.stem}_report.txt")
    report_path.write_text(_render_summary(summary), encoding="utf-8")
    return output_path


def _iter_story_roots(doc):
    # The body plus every header/footer part — i.e. each section's stories.
    yield doc.element.body
    for part in doc.part.package.parts:
        element = getattr(part, "element", None)
        if element is not None and element.tag in (_HDR, _FTR):
            yield element


def _paragraph_location(root, paragraph):
    if root.tag in (_HDR, _FTR):
        return "headers_footers"
    for _ in paragraph.iterancestors(_TBL):
        return "tables"
    return "body"


def _format_paragraph(paragraph):
    return {key: run_pass(paragraph) for key, run_pass in _PARAGRAPH_PASSES}


def _unwrap_smart_tags(paragraph):
    # Smart tags wrap runs in an inert <w:smartTag> element; promoting the runs
    # out declutters the paragraph and lets them take part in run merging.
    count = 0
    smart_tags = paragraph.findall(f".//{_SMART_TAG}")
    while smart_tags:
        for smart_tag in smart_tags:
            parent = smart_tag.getparent()
            if parent is None:
                continue
            index = list(parent).index(smart_tag)
            for child in list(smart_tag):
                if child.tag == _SMART_TAG_PR:
                    continue
                parent.insert(index, child)
                index += 1
            parent.remove(smart_tag)
            count += 1
        smart_tags = paragraph.findall(f".//{_SMART_TAG}")
    return count


def _remove_proof_errors(paragraph):
    count = 0
    for proof_error in paragraph.findall(f".//{_PROOF_ERR}"):
        parent = proof_error.getparent()
        if parent is not None:
            parent.remove(proof_error)
            count += 1
    return count


def _remove_orphan_field_runs(paragraph):
    # A Word field is delimited by <w:fldChar> begin/end runs. A delimiter that
    # is unbalanced AND carries no text is stale clutter, safe to drop.
    open_begins = []
    orphans = []
    for run in paragraph.findall(f".//{_R}"):
        fld_char = run.find(_FLD_CHAR)
        if fld_char is None:
            continue
        fld_type = fld_char.get(_FLD_CHAR_TYPE)
        if fld_type == "begin":
            open_begins.append(run)
        elif fld_type == "end":
            if open_begins:
                open_begins.pop()
            else:
                orphans.append(run)
    orphans.extend(open_begins)
    
    count = 0
    for run in orphans:
        if _run_text(run).strip():
            continue
        parent = run.getparent()
        if parent is not None:
            parent.remove(run)
            count += 1
    return count


def _reset_manual_colours(paragraph):
    count = 0
    for run in paragraph.iter(_R):
        rPr = run.find(_RPR)
        if rPr is None:
            continue
        colour = rPr.find(_COLOR)
        if colour is not None:
            rPr.remove(colour)
            count += 1
        if len(rPr) == 0:
            run.remove(rPr)
    return count


def _strip_blank_run_formatting(paragraph):
    count = 0
    for run in paragraph.iter(_R):
        rPr = run.find(_RPR)
        if rPr is None:
            continue
        if not _is_text_run(run) or _run_text(run).strip():
            continue
        stripped = False
        for tag in _TEXT_ONLY_PROPERTIES:
            disallowed = rPr.find(tag)
            if disallowed is not None:
                rPr.remove(disallowed)
                stripped = True
        if stripped:
            count += 1
        if len(rPr) == 0:
            run.remove(rPr)
    return count


def _merge_disjointed_runs(paragraph):
    merged = _merge_runs(paragraph)
    for hyperlink in paragraph.iter(_HYPERLINK):
        merged += _merge_runs(hyperlink)
    return merged


# Ordered cleanup passes applied to every paragraph. Order matters: structural
# unwrapping/removal first so promoted runs can merge, colour reset before the
# merge so run signatures line up, merge last.
_PARAGRAPH_PASSES = (
    ("smart_tags", _unwrap_smart_tags),
    ("proof_errors", _remove_proof_errors),
    ("orphan_fields", _remove_orphan_field_runs),
    ("manual_colours", _reset_manual_colours),
    ("blank_run_formatting", _strip_blank_run_formatting),
    ("merged_runs", _merge_disjointed_runs),
)


def _merge_runs(parent):
    # Drop empty text runs, then merge each stretch of consecutive text runs
    # that share identical run properties into the first run of the stretch.
    removed = 0
    for run in [child for child in parent if child.tag == _R]:
        if _is_text_run(run) and not _run_text(run):
            parent.remove(run)
            removed += 1
    
    merged = 0
    accumulator = None
    accumulator_signature = None
    for child in list(parent):
        if child.tag == _PROOF_ERR:
            # Spell/grammar markers fragment runs without being formatting.
            continue
        if child.tag != _R or not _is_text_run(child):
            accumulator = None
            continue
        signature = _run_signature(child)
        if accumulator is not None and signature == accumulator_signature:
            for text in child.findall(_T):
                accumulator.append(text)
            parent.remove(child)
            merged += 1
        else:
            accumulator = child
            accumulator_signature = signature
    return removed + merged


def _is_text_run(run):
    # A run carrying only text — no drawings, breaks, tabs, fields, etc. Only
    # these can be merged or dropped without reordering content.
    for child in run:
        if child.tag != _RPR and child.tag != _T:
            return False
    return True


def _run_text(run):
    return "".join(text.text or "" for text in run.findall(_T))


def _run_signature(run):
    # Order-independent fingerprint of a run's properties. Two runs with equal
    # signatures render identically, so their text can be safely concatenated.
    rPr = run.find(_RPR)
    if rPr is None:
        return ()
    return tuple(sorted(
        (child.tag, tuple(sorted(child.attrib.items())))
        for child in rPr
    ))


def _render_summary(summary):
    locations = summary["locations"]
    lines = [
        "Format cleanup summary",
        "",
        f"Paragraphs scanned: {summary['paragraphs_scanned']} "
        f"(body {locations['body']}, tables {locations['tables']}, "
        f"headers/footers {locations['headers_footers']})",
        "",
    ]
    fixes = summary["fixes"]
    if any(fixes.values()):
        for key, label in _FIX_LABELS:
            lines.append(f"{label}: {fixes[key]}")
    else:
        lines.append("No formatting changes were needed.")
    return "\n".join(lines) + "\n"
