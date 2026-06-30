"""
Builds a structural model of a PDF's sections so that instructions like
"remove the Termination Clause section" can be resolved to actual content.

Heuristic: a line is treated as a heading if it is meaningfully larger than
the document's most common ("body") font size, or bold at-or-above body
size, and short enough to plausibly be a title rather than a sentence.

This is intentionally heuristic rather than relying on PDF bookmarks/outline,
since many real-world PDFs (especially ones exported from web tools) don't
carry a populated outline tree.
"""

from collections import Counter
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import fitz  # PyMuPDF

BOLD_FLAG = 1 << 4  # fitz span flag bit for bold text
HEADING_SIZE_RATIO = 1.15
HEADING_MAX_WORDS = 12


@dataclass
class BlockRef:
    page: int
    bbox: Tuple[float, float, float, float]
    text: str


@dataclass
class Section:
    id: str
    title: str
    start_page: int
    end_page: int
    blocks: List[BlockRef] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(b.text for b in self.blocks)


def extract_sections(pdf_bytes: bytes) -> List[Section]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        lines = _collect_lines(doc)
        if not lines:
            return []

        body_size = _most_common_size(lines)
        sections: List[Section] = []
        current: Optional[Section] = None
        section_count = 0

        for ln in lines:
            if _looks_like_heading(ln, body_size):
                section_count += 1
                if current is not None:
                    sections.append(current)
                current = Section(
                    id=f"sec_{section_count}",
                    title=ln["text"],
                    start_page=ln["page"],
                    end_page=ln["page"],
                )
                current.blocks.append(BlockRef(ln["page"], ln["bbox"], ln["text"]))
            else:
                if current is None:
                    section_count += 1
                    current = Section(
                        id=f"sec_{section_count}",
                        title="(untitled preamble)",
                        start_page=ln["page"],
                        end_page=ln["page"],
                    )
                current.blocks.append(BlockRef(ln["page"], ln["bbox"], ln["text"]))
                current.end_page = ln["page"]

        if current is not None:
            sections.append(current)
        return sections
    finally:
        doc.close()


def _collect_lines(doc: fitz.Document) -> List[dict]:
    lines: List[dict] = []
    for page_no in range(doc.page_count):
        page = doc[page_no]
        page_dict = page.get_text("dict")
        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:  # 0 = text block
                continue
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                if not spans:
                    continue
                text = "".join(s["text"] for s in spans).strip()
                if not text:
                    continue
                size = max(s["size"] for s in spans)
                bold = any(int(s.get("flags", 0)) & BOLD_FLAG for s in spans)
                lines.append(
                    {
                        "page": page_no,
                        "bbox": tuple(line["bbox"]),
                        "text": text,
                        "size": size,
                        "bold": bold,
                    }
                )
    return lines


def _most_common_size(lines: List[dict]) -> float:
    rounded = [round(ln["size"], 1) for ln in lines]
    return Counter(rounded).most_common(1)[0][0]


def _looks_like_heading(line: dict, body_size: float) -> bool:
    word_count = len(line["text"].split())
    if word_count > HEADING_MAX_WORDS:
        return False
    larger = line["size"] >= body_size * HEADING_SIZE_RATIO
    bold_at_body = line["bold"] and line["size"] >= body_size
    return larger or bold_at_body
