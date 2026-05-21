# CSAS Publication Formatting Specs

`csas_publication.json` is a machine-readable specification of the Microsoft
Word styles used in CSAS (Canadian Science Advisory Secretariat) publications.
A formatting tool reads it to convert a plain `.docx` into CSAS format by
creating/updating each named style with the properties listed.

It was derived by extracting and resolving the style definitions in the ten
templates under `data/2026_Templates/` (five publication types × English/French).

## Formatting options

The Format feature is intended to offer two choices:

1. **CSAS Publication** — apply one of the templates in `csas_publication.json`.
2. **Do not change source formats** — leave the document untouched (no spec).

## The two templates

`csas_publication.json` → `templates` contains two entries, because the source
documents fall into two distinct formatting families:

| Template                   | Covers                                                                                 | Headings                                                                                                     |
|----------------------------|----------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------|
| `advisory_response_report` | Science Advisory Report (SAR-AS), Science Response Report (SRR-RS), FSAR-PAS, FSRR-PRS | H1 16 pt, H2 14 pt, H3–H5 12/11 pt                                                                           |
| `research_document`        | Research Document (RES)                                                                | H1–H3 12 pt, H4–H5 11 pt; adds cover page, Table of Contents, Abstract, Appendix and numbered-heading styles |

Both share the same body text, captions, citations, lists and page setup.

For a full style-by-style comparison of the two templates — the shared core, the
styles that differ, the structural divergence, and why they are kept separate —
see [`spec_differences.md`](../spec_differences.md).

## Schema

```
_meta                     spec metadata, units, conventions
templates
  <template_id>
    display_name
    applies_to            publication types this template formats
    source_documents      templates it was derived from
    page_setup            page size, margins, header/footer distance (pt)
    document_defaults     default font / size / line spacing
    paragraph_styles      { <styleId>: <style> }
    character_styles      { <styleId>: <style> }
    list_marker_note
non_standard_styles       styles found in the templates but NOT part of the spec
```

Each `<style>` has:

- `style_name` — the Word display name; `based_on` — the inherited style.
- `purpose` — what the style is for.
- `used_in` — how many source documents applied it.
- `also_named` — other styleIds the same style appears under (mostly the
  French-language styleIds; the JSON key is the canonical English styleId).
- `run` — character formatting: `font`, `size_pt`, `bold`, `italic`,
  `all_caps`, `color` (hex `RRGGBB` or `automatic`), `underline`.
- `paragraph` — paragraph formatting: `alignment`, `line_spacing`,
  `space_before_pt` / `space_after_pt`, the four indents (pt),
  `keep_with_next`, `keep_lines_together`, `contextual_spacing`,
  `outline_level`.
- `linked_character_style` / `auto_numbered` / `list` — present when relevant.
- `source_variations` — present only when the source documents disagreed; the
  value in the spec is the majority/normalised one, and this lists what was
  seen. (See "Normalisation decisions" below.)

Sizes are in points: 1 inch = 72 pt, 1 cm ≈ 28.35 pt.

## Consistency findings

The templates were checked style-by-style across all ten documents:

- **Consistent across all 10 documents** — Body Text (and its bold/italic/
  centred variants), Caption-Figure, Caption-Table, citation,
  citation-translated, Blockquote, and the four list styles. Body text is
  uniformly **Arial 11 pt, single line spacing, 6 pt before/after**. Page setup
  is uniform: **Letter, 1″ margins on all sides**.
- **Headings differ between the two families** (the reason for two templates):
  the advisory/response reports use a larger heading scale than the Research
  Document.
- **Only used styles are included** — "used" means a paragraph/run in the
  document body, headers, footers or notes actually carries the style. Heading
  1–5 are used in every document. Heading 6–9 are *not* in the spec: although
  the templates define those styles and reference them inside multi-level list
  definitions (`numbering.xml`), no content is formatted with them. No table
  styles are applied anywhere either, so none are specified.
- **Minor template drift** (one document out of a group disagreeing) is recorded
  per style under `source_variations`.

## Normalisation decisions

Where the source templates disagreed, the spec resolves it as follows:

- **Majority wins.** For drift such as a missing `keep_lines_together` or an
  off-by-a-fraction indent, the value used in most source documents is taken.
- **Heading colours → automatic.** Some headings carried a manual blue
  (`4F81BD`) in some documents (mainly RES English) but not others, and the
  blue was applied inconsistently across heading levels — so it is treated as
  drift and normalised to automatic (black). The original blue is still listed
  under `source_variations` if you want to restore it.
- **Linked character styles** (e.g. `Heading1Char`) are not given separate
  entries — Word recreates them automatically. They are noted on the parent
  paragraph style via `linked_character_style`.
- **Non-standard styles** — a few styles found applied in the templates are
  clearly imported clutter or paste artifacts (e.g. `StyleHelvetica10pt`,
  `normaltextrun`). They are listed under `non_standard_styles` and are **not**
  part of the spec.

## Updating

When new annual templates are issued, re-derive the spec from them rather than
hand-editing — the source documents are the authority.

<br>

---

# Spec Differences in CSAS templates: advisory/response vs. research document

A comparison of the two templates in `data/format_specs/csas_publication.json`,
to record why they are kept separate. Derived from the ten source documents in
`data/2026_Templates/`.

## Summary

- **Each template is internally consistent** across its source documents. The
  only within-template wobble is minor drift, recorded per style under
  `source_variations` in the spec.
- **The two templates are not consistent with each other, and shouldn't be.**
  `Heading1`/`Heading2` are deliberately sized differently, and the Research
  Document carries a whole front-matter/appendix style set the short reports
  don't have. Keeping them as two templates is the right call.

## Shared core — consistent

The two templates share 22 styles, and **14 are byte-for-byte identical**:
`BodyText`, `BodyTextBold`, `BodyTextCentered`, `Blockquote`, `Heading3`,
`Heading4`, `Caption-Figure`, `Caption-Table`, `ListBullet`, `ListNumber`,
`citation`, `citation-translated`, `Header`, `Hyperlink`.

Body text, captions, citations and level-1 lists are the same in both templates.

## Shared styles that differ (8 of 22)

| Style                         | Advisory / Response             | Research Document             |
|-------------------------------|---------------------------------|-------------------------------|
| `Heading1`                    | **16 pt**, 12 pt before         | **12 pt**, 18 pt before       |
| `Heading2`                    | **14 pt**, centered             | **12 pt**, left-aligned       |
| `Normal`                      | 0 pt before/after               | 6 pt before/after ¹           |
| `Footer`                      | 0 pt before/after               | 6 pt before/after             |
| `CoverPageHeaderCSAS`         | based on `BodyText`, 0 pt after | based on `Normal`, 6 pt after |
| `Heading5`                    | indent 28.1 pt                  | indent 28.35 pt ²             |
| `ListBullet2` / `ListNumber2` | style indent 36 pt              | style indent 0 pt ³           |

¹ For body text the *visible* result is the same — both end at 6 pt
before/after. The advisory template puts that spacing on `BodyText`; the
Research Document puts it on `Normal` and `BodyText` inherits it.

² 0.99 cm vs 1.0 cm — rounding noise.

³ Level-2 list items are still indented in both — the indent comes from the
numbering definition; only the style-level indent differs.

## Structural divergence — styles unique to each template

**Research Document only (19 styles).** A Research Document is a long-form
publication with a cover page, table of contents, abstract and appendices —
sections the short advisory/response reports don't have:

- Numbered-heading variants: `Heading1withnumbers` … `Heading5withnumbers`
- `AbstractHeading`
- Appendix headings: `AppendixH1`, `AppendixH2`, `AppendixH3`
- Table of Contents: `TABLEOFCONTENTS`, `TOC1`, `TOC2`, `TOC3`
- Cover page: `CoverAuthor`, `CoverAddress`, `CoverDocumenttitle`,
  `CoverPageHeaderseries`, `ForewordPublishedby2ndpage`

**Advisory / Response Report only (4 styles):** `BodyTextItalic`,
`CoverPageHeaderregions`, `PageHeaderRegionsNameofthereport`, `PageNumber`.

## Note

`Heading6`–`Heading9` are **not** in either template. The templates define
those styles and reference them inside multi-level list definitions
(`numbering.xml`), but no document content is actually formatted with them.

<br><br><br>
