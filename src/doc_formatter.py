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
_COLOR = qn("w:color")
_PROOF_ERR = qn("w:proofErr")
_HYPERLINK = qn("w:hyperlink")
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


def format_document_bytes(docx_bytes):
    doc = Document(io.BytesIO(docx_bytes))
    
    paragraphs = 0
    colours_reset = 0
    runs_merged = 0
    for root in _iter_story_roots(doc):
        for paragraph in root.iter(_P):
            paragraphs += 1
            reset, merged = _format_paragraph(paragraph)
            colours_reset += reset
            runs_merged += merged
    
    logger.info(
        f"[formatter] scanned {paragraphs} paragraphs | "
        f"reset {colours_reset} manual colour(s) | merged {runs_merged} disjointed run(s)"
    )
    
    output = io.BytesIO()
    doc.save(output)
    return output.getvalue()


def format_document(file_path):
    path = Path(file_path)
    output_path = path.with_stem(f"{path.stem}_formatted")
    output_path.write_bytes(format_document_bytes(path.read_bytes()))
    return output_path


def _iter_story_roots(doc):
    # The body plus every header/footer part — i.e. each section's stories.
    yield doc.element.body
    for part in doc.part.package.parts:
        element = getattr(part, "element", None)
        if element is not None and element.tag in (_HDR, _FTR):
            yield element


def _format_paragraph(paragraph):
    colours_reset = 0
    for run in paragraph.iter(_R):
        if _clean_run(run):
            colours_reset += 1
    
    runs_merged = _merge_runs(paragraph)
    for hyperlink in paragraph.iter(_HYPERLINK):
        runs_merged += _merge_runs(hyperlink)
    return colours_reset, runs_merged


def _clean_run(run):
    rPr = run.find(_RPR)
    if rPr is None:
        return False
    
    colour = rPr.find(_COLOR)
    if colour is not None:
        rPr.remove(colour)
    
    if _is_text_run(run) and not _run_text(run).strip():
        for tag in _TEXT_ONLY_PROPERTIES:
            disallowed = rPr.find(tag)
            if disallowed is not None:
                rPr.remove(disallowed)
    
    if len(rPr) == 0:
        run.remove(rPr)
    return colour is not None


def _merge_runs(parent):
    # Drop empty text runs, then merge each stretch of consecutive text runs
    # that share identical run properties into the first run of the stretch.
    for run in [child for child in parent if child.tag == _R]:
        if _is_text_run(run) and not _run_text(run):
            parent.remove(run)
    
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
    return merged


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
