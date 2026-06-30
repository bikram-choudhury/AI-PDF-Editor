"""
Produces a plain-text summary of what changed between the original and
updated PDF, for the frontend's before/after preview panel.

Note: returns plain text, not HTML, matching how the frontend currently
renders these fields (interpolated directly into JSX text content rather
than via dangerouslySetInnerHTML). The field names (diffHtmlBefore/After)
are kept as-is for contract compatibility with the existing frontend types;
if richer inline highlighting is wanted later, this is the function to
extend to emit <ins>/<del> markup and switch the frontend to render it as HTML.
"""

import difflib

import fitz  # PyMuPDF


def extract_full_text(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        return "\n".join(page.get_text("text") for page in doc)
    finally:
        doc.close()


def summarize_diff(before_text: str, after_text: str) -> tuple[str, str]:
    before_lines = [ln for ln in before_text.splitlines() if ln.strip()]
    after_lines = [ln for ln in after_text.splitlines() if ln.strip()]
    matcher = difflib.SequenceMatcher(a=before_lines, b=after_lines)

    removed: list[str] = []
    added: list[str] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ("delete", "replace"):
            removed.extend(before_lines[i1:i2])
        if tag in ("insert", "replace"):
            added.extend(after_lines[j1:j2])

    before_summary = "Removed:\n" + ("\n".join(removed) if removed else "(nothing removed)")
    after_summary = "Added:\n" + ("\n".join(added) if added else "(nothing added)")
    return before_summary, after_summary
