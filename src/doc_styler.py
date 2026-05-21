import io
import json
import logging
from pathlib import Path

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

logger = logging.getLogger("doc_tools.styler")

_SPEC_PATH = (
        Path(__file__).resolve().parents[1]
        / "data" / "format_specs" / "csas_publication.json"
)

_ALIGNMENT = {
    "left": WD_ALIGN_PARAGRAPH.LEFT,
    "center": WD_ALIGN_PARAGRAPH.CENTER,
    "right": WD_ALIGN_PARAGRAPH.RIGHT,
    "both": WD_ALIGN_PARAGRAPH.JUSTIFY,
}

_STYLE_TYPE = {
    "paragraph": WD_STYLE_TYPE.PARAGRAPH,
    "character": WD_STYLE_TYPE.CHARACTER,
}

# Theme-font attributes on <w:rFonts>: while present they override the plain
# ascii/hAnsi font, so they are stripped when the spec pins an explicit font.
_FONT_THEME_ATTRS = ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme")

# Elements that, per the OOXML schema, follow <w:contextualSpacing> inside
# <w:pPr> — used to insert it in a schema-valid position.
_AFTER_CONTEXTUAL_SPACING = (
    "w:mirrorIndents", "w:suppressOverlap", "w:jc", "w:textDirection",
    "w:textAlignment", "w:textboxTightWrap", "w:outlineLvl", "w:divId",
    "w:cnfStyle", "w:rPr", "w:sectPr", "w:pPrChange",
)


def load_spec():
    return json.loads(_SPEC_PATH.read_text(encoding="utf-8"))


def available_templates():
    # Ordered {template_id: display_name} for the CSAS formatting spec.
    return {tid: tpl["display_name"]
            for tid, tpl in load_spec()["templates"].items()}


def apply_format_spec_bytes(docx_bytes, template_id):
    template = load_spec()["templates"][template_id]
    doc = Document(io.BytesIO(docx_bytes))
    
    summary = {
        "template": template["display_name"],
        "styles_created": 0,
        "styles_updated": 0,
        "sections_adjusted": 0,
    }
    
    spec_styles = dict(template["paragraph_styles"])
    spec_styles.update(template["character_styles"])
    _apply_styles(doc, spec_styles, summary)
    _apply_page_setup(doc, template["page_setup"], summary)
    
    logger.info(
        f"[styler] {template['display_name']}: "
        f"{summary['styles_created']} styles created, "
        f"{summary['styles_updated']} updated, "
        f"{summary['sections_adjusted']} sections"
    )
    
    output = io.BytesIO()
    doc.save(output)
    return output.getvalue(), summary


def _apply_styles(doc, spec_styles, summary):
    # Pass 1: make sure every spec style exists, keyed by its CSAS styleId.
    resolved = {}
    for style_id, entry in spec_styles.items():
        style = _find_style(doc, style_id, entry["style_name"])
        if style is None:
            style = doc.styles.add_style(
                entry["style_name"], _STYLE_TYPE[entry["style_type"]])
            style.element.set(qn("w:styleId"), style_id)
            summary["styles_created"] += 1
        else:
            summary["styles_updated"] += 1
        resolved[style_id] = style
    
    # Pass 2: apply formatting. Every base style now exists for linking.
    for style_id, entry in spec_styles.items():
        style = resolved[style_id]
        _apply_run(style, entry["run"])
        if entry["style_type"] == "paragraph":
            _apply_paragraph(style, entry["paragraph"])
        based_on = entry.get("based_on")
        if based_on in resolved:
            style.base_style = resolved[based_on]


def _find_style(doc, style_id, style_name):
    # Word's built-in styles keep stable styleIds (Normal, BodyText,
    # Heading1...); custom CSAS styles are matched by name as a fallback.
    for style in doc.styles:
        if style.style_id == style_id:
            return style
    for style in doc.styles:
        if style.name == style_name:
            return style
    return None


def _apply_run(style, run):
    font = style.font
    if run.get("font"):
        font.name = run["font"]
        _strip_font_themes(style)
    if run.get("size_pt"):
        font.size = Pt(run["size_pt"])
    font.bold = bool(run.get("bold"))
    font.italic = bool(run.get("italic"))
    font.all_caps = bool(run.get("all_caps"))
    if run.get("underline"):
        font.underline = True
    if run.get("color", "automatic") == "automatic":
        _clear_run_colour(style)
    else:
        font.color.rgb = RGBColor.from_string(run["color"])


def _strip_font_themes(style):
    rPr = style.element.find(qn("w:rPr"))
    rFonts = rPr.find(qn("w:rFonts")) if rPr is not None else None
    if rFonts is None:
        return
    for attr in _FONT_THEME_ATTRS:
        if qn(attr) in rFonts.attrib:
            del rFonts.attrib[qn(attr)]


def _clear_run_colour(style):
    # No <w:color> means the run colour falls through to automatic (black).
    rPr = style.element.find(qn("w:rPr"))
    colour = rPr.find(qn("w:color")) if rPr is not None else None
    if colour is not None:
        rPr.remove(colour)


def _apply_paragraph(style, para):
    fmt = style.paragraph_format
    fmt.alignment = _ALIGNMENT[para["alignment"]]
    fmt.space_before = Pt(para["space_before_pt"])
    fmt.space_after = Pt(para["space_after_pt"])
    fmt.line_spacing = 1.0
    fmt.left_indent = Pt(para["indent_left_pt"])
    fmt.right_indent = Pt(para["indent_right_pt"])
    # A hanging indent is a negative first-line indent in OOXML.
    if para["hanging_indent_pt"]:
        fmt.first_line_indent = Pt(-para["hanging_indent_pt"])
    else:
        fmt.first_line_indent = Pt(para["first_line_indent_pt"])
    fmt.keep_with_next = para["keep_with_next"]
    fmt.keep_together = para["keep_lines_together"]
    fmt.page_break_before = para["page_break_before"]
    
    pPr = style.element.get_or_add_pPr()
    _set_outline_level(pPr, para["outline_level"])
    _set_contextual_spacing(pPr, para["contextual_spacing"])


def _set_outline_level(pPr, level):
    existing = pPr.find(qn("w:outlineLvl"))
    if level is None:
        if existing is not None:
            pPr.remove(existing)
        return
    if existing is None:
        existing = pPr.get_or_add_outlineLvl()
    existing.set(qn("w:val"), str(level))


def _set_contextual_spacing(pPr, enabled):
    existing = pPr.find(qn("w:contextualSpacing"))
    if enabled and existing is None:
        pPr.insert_element_before(
            OxmlElement("w:contextualSpacing"), *_AFTER_CONTEXTUAL_SPACING)
    elif not enabled and existing is not None:
        pPr.remove(existing)


def _apply_page_setup(doc, page, summary):
    margins = page["margins_pt"]
    for section in doc.sections:
        section.page_width = Pt(page["page_width_pt"])
        section.page_height = Pt(page["page_height_pt"])
        section.top_margin = Pt(margins["top"])
        section.bottom_margin = Pt(margins["bottom"])
        section.left_margin = Pt(margins["left"])
        section.right_margin = Pt(margins["right"])
        section.header_distance = Pt(page["header_distance_pt"])
        section.footer_distance = Pt(page["footer_distance_pt"])
        summary["sections_adjusted"] += 1
