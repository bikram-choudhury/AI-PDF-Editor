"""
Applies a confirmed edit plan to the original PDF bytes.

Strategy (matches the hybrid approach from the architecture doc):
- Deletions are true PDF surgery: redact the section's actual text spans in
  place. This is exact and never needs reflow, since removing content
  doesn't require making room elsewhere.
- Additions (append / insert) can't be reflowed into existing pages without
  a full layout engine, so new content is rendered onto freshly created
  page(s) sized to match the document, then spliced in immediately after
  the target section. This preserves the untouched original pages exactly
  and keeps the new content visually consistent (same page size/margins).

Known v1 limitation: very long additions that overflow a single new page
are not currently auto-paginated onto a second page (PyMuPDF's textbox API
doesn't return the unfit remainder text). Fine for paragraph-length
additions; flagged here for anyone extending this.
"""

from typing import List, Optional

import fitz  # PyMuPDF

from .pdf_structure import Section
from .store import ParsedOperation

PAGE_MARGIN = 56
TITLE_FONT_SIZE = 14
BODY_FONT_SIZE = 11


def apply_edit_plan(
    pdf_bytes: bytes, sections: List[Section], operations: List[ParsedOperation]
) -> bytes:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    section_by_id = {s.id: s for s in sections}

    _apply_deletions(doc, section_by_id, operations)
    _apply_additions(doc, section_by_id, operations)

    out = doc.tobytes(garbage=4, deflate=True)
    doc.close()
    return out


def _apply_deletions(doc: fitz.Document, section_by_id: dict, operations: List[ParsedOperation]) -> None:
    for op in operations:
        if op.op != "delete_section" or not op.target_section_id:
            continue
        section = section_by_id.get(op.target_section_id)
        if section:
            _delete_section(doc, section)


def _delete_section(doc: fitz.Document, section: Section) -> None:
    pages_touched = sorted({b.page for b in section.blocks})
    for page_no in pages_touched:
        page = doc[page_no]
        for block in section.blocks:
            if block.page == page_no:
                page.add_redact_annot(fitz.Rect(block.bbox), fill=(1, 1, 1))
    for page_no in pages_touched:
        doc[page_no].apply_redactions()
    # Drop pages that are now fully blank as a result of this deletion.
    for page_no in sorted(pages_touched, reverse=True):
        if page_no < doc.page_count and _page_is_blank(doc[page_no]):
            doc.delete_page(page_no)


def _page_is_blank(page: fitz.Page) -> bool:
    return len(page.get_text("text").strip()) == 0


def _apply_additions(doc: fitz.Document, section_by_id: dict, operations: List[ParsedOperation]) -> None:
    additions = [op for op in operations if op.op in ("append_to_section", "insert_new_section")]

    # Insert from the bottom of the document up, so earlier insertions don't
    # shift the page indices that later anchors depend on.
    def anchor_page(op: ParsedOperation) -> int:
        section = section_by_id.get(op.target_section_id) if op.target_section_id else None
        return section.end_page if section else doc.page_count - 1

    additions.sort(key=anchor_page, reverse=True)

    for op in additions:
        section = section_by_id.get(op.target_section_id) if op.target_section_id else None
        anchor = min(section.end_page if section else doc.page_count - 1, doc.page_count - 1)
        like_page = doc[anchor]
        title = op.new_title if op.op == "insert_new_section" else None
        new_page = _render_content_page(doc, like_page, title, op.content or "")
        _move_page_after(doc, new_page, anchor)


def _render_content_page(
    doc: fitz.Document, like_page: fitz.Page, title: Optional[str], body: str
) -> fitz.Page:
    rect = like_page.rect
    page = doc.new_page(width=rect.width, height=rect.height)

    cursor_y = PAGE_MARGIN
    if title:
        page.insert_textbox(
            fitz.Rect(PAGE_MARGIN, cursor_y, rect.width - PAGE_MARGIN, cursor_y + 30),
            title,
            fontsize=TITLE_FONT_SIZE,
            fontname="helv",
            color=(0, 0, 0),
        )
        cursor_y += 40

    page.insert_textbox(
        fitz.Rect(PAGE_MARGIN, cursor_y, rect.width - PAGE_MARGIN, rect.height - PAGE_MARGIN),
        body,
        fontsize=BODY_FONT_SIZE,
        fontname="helv",
        color=(0, 0, 0),
    )
    return page


def _move_page_after(doc: fitz.Document, page: fitz.Page, anchor_index: int) -> None:
    # The new page was appended at the document's end; move it to sit
    # immediately after the anchor section's last page.
    doc.move_page(page.number, anchor_index + 1)
