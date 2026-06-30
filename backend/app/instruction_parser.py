"""
Maps plain-language instructions to a structured edit plan, given the
document's section outline. Uses Claude's forced tool-use so the model's
output is always a well-formed list of operations rather than free text
that downstream code would need to re-interpret.

Note on scope: the original architecture doc described a separate
embeddings-based semantic-matching step for resolving ambiguous section
references. This implementation has the LLM do that matching directly,
since it already sees the full section outline in context — this keeps
the system simpler with one fewer moving part, at the cost of matching
quality being only as good as a single model call rather than a dedicated
retrieval step. Revisit if matching accuracy on long/many-section
documents turns out to need it.
"""

import json
import uuid
from typing import List, Optional

import anthropic

from . import config
from .pdf_structure import Section
from .store import ParsedOperation

CONFIDENCE_THRESHOLD = 0.7

EDIT_PLAN_TOOL = {
    "name": "submit_edit_plan",
    "description": "Submit the structured list of edit operations parsed from the user's instructions.",
    "input_schema": {
        "type": "object",
        "properties": {
            "operations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "op": {
                            "type": "string",
                            "enum": ["delete_section", "append_to_section", "insert_new_section"],
                        },
                        "target_section_id": {
                            "type": ["string", "null"],
                            "description": (
                                "For delete_section/append_to_section: the section being acted on. "
                                "For insert_new_section: the section to insert after, or null to "
                                "insert at the end of the document."
                            ),
                        },
                        "candidate_section_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "If the reference is ambiguous, every plausible section id.",
                        },
                        "new_title": {
                            "type": ["string", "null"],
                            "description": "Title for the new section. Required for insert_new_section.",
                        },
                        "content": {
                            "type": ["string", "null"],
                            "description": "New body text to add, for append_to_section / insert_new_section.",
                        },
                        "confidence": {
                            "type": "number",
                            "description": "0 to 1 confidence in target_section_id / insertion point.",
                        },
                        "rationale": {
                            "type": "string",
                            "description": "One short sentence explaining the match, or the ambiguity.",
                        },
                    },
                    "required": ["op", "confidence", "rationale"],
                },
            }
        },
        "required": ["operations"],
    },
}

SYSTEM_PROMPT = """You convert a user's plain-language PDF editing instructions into a structured edit plan.

You are given the document's section outline (id, title, short text preview) and the user's instructions.

Rules:
- Decompose compound instructions ("remove X, add Y, insert Z") into separate operations.
- For delete_section and append_to_section, target_section_id must be the single best-matching section id.
- If multiple sections are plausible matches for the same instruction, still set target_section_id to your
  single best guess, but also list every plausible id in candidate_section_ids and lower your confidence.
- For insert_new_section, target_section_id is the section the new content should be inserted after
  (use null only if the instruction clearly means "at the end of the document").
- If you cannot find any plausible target at all, set target_section_id to null and confidence below 0.3.
- Always call submit_edit_plan exactly once, with one entry per distinct requested change.
"""


def parse_instructions(sections: List[Section], instructions: str) -> List[ParsedOperation]:
    if not config.ANTHROPIC_API_KEY:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Add it to your .env file to enable instruction parsing."
        )

    outline = [{"id": s.id, "title": s.title, "preview": s.text[:200]} for s in sections]
    user_message = (
        f"Section outline:\n{json.dumps(outline, indent=2)}\n\nInstructions:\n{instructions}"
    )

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        tools=[EDIT_PLAN_TOOL],
        tool_choice={"type": "tool", "name": "submit_edit_plan"},
        messages=[{"role": "user", "content": user_message}],
    )

    tool_use = next((b for b in response.content if b.type == "tool_use"), None)
    if tool_use is None:
        raise RuntimeError("Claude did not return a structured edit plan for this request.")

    raw_operations = tool_use.input.get("operations", [])
    section_by_id = {s.id: s for s in sections}
    return [_to_parsed_operation(raw, section_by_id) for raw in raw_operations]


def _to_parsed_operation(raw: dict, section_by_id: dict) -> ParsedOperation:
    op = raw["op"]
    target_id: Optional[str] = raw.get("target_section_id")
    candidates: List[str] = raw.get("candidate_section_ids") or []
    confidence = float(raw.get("confidence", 0.5))
    target_section = section_by_id.get(target_id) if target_id else None

    target_missing = op != "insert_new_section" and target_id is not None and target_section is None
    needs_confirmation = (
        confidence < CONFIDENCE_THRESHOLD or len(candidates) > 1 or target_missing
    )

    label = _build_label(op, target_section, raw.get("new_title"))

    ambiguity_note = None
    if needs_confirmation:
        named_candidates = [section_by_id[c].title for c in candidates if c in section_by_id]
        if named_candidates:
            ambiguity_note = "Multiple possible matches: " + ", ".join(named_candidates)
        else:
            ambiguity_note = raw.get("rationale")

    return ParsedOperation(
        id=str(uuid.uuid4())[:8],
        op=op,
        target_section_id=target_id,
        candidate_section_ids=candidates,
        new_title=raw.get("new_title"),
        content=raw.get("content"),
        confidence=confidence,
        needs_confirmation=needs_confirmation,
        label=label,
        ambiguity_note=ambiguity_note,
    )


def _build_label(op: str, target_section: Optional[Section], new_title: Optional[str]) -> str:
    if op == "delete_section":
        return f'Delete "{target_section.title}"' if target_section else "Delete — target section not found"
    if op == "append_to_section":
        return f'Add to "{target_section.title}"' if target_section else "Add content — target section not found"
    anchor = f' after "{target_section.title}"' if target_section else " at end of document"
    return f'Insert new section "{new_title or "Untitled"}"{anchor}'
