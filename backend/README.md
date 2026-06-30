# Redraft backend

FastAPI backend for the instruction-driven PDF editor. Implements the
pipeline from the architecture doc: extract document structure → parse
instructions into a structured edit plan (Claude tool-use) → apply the plan
to the PDF (PyMuPDF) → serve a time-limited download link.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in ANTHROPIC_API_KEY
uvicorn app.main:app --reload --port 8000
```

## Endpoints

### `POST /api/analyze`
multipart/form-data: `file` (PDF), `instructions` (string)
→ `AnalyzeResponse` — `{ jobId, sourceFileName, operations[] }`, matching the
frontend's `types.ts` exactly.

### `POST /api/jobs/{job_id}/apply`
→ `ApplyResponse` — `{ jobId, downloadUrl, downloadFileName, diffHtmlBefore, diffHtmlAfter, expiresInSeconds }`
Returns **409** if any operation in the plan still has `needsConfirmation: true`
— mirrors the frontend's disabled "Confirm & apply" button, enforced
server-side too.

### `GET /api/download/{token}`
Streams the finished PDF. The token is single-purpose and expires after
`DOWNLOAD_TTL_SECONDS` (default 30 min) — there's no real object storage
here, so this is the in-memory stand-in for a signed S3/Blob URL described
in the architecture doc.

## How editing actually works

- **Structure extraction** (`pdf_structure.py`): walks every line via PyMuPDF,
  finds the most common font size in the document (the "body" size), and
  treats meaningfully-larger or bold-at-body-size short lines as headings.
  No reliance on PDF bookmarks, since many real PDFs don't have them populated.

- **Instruction parsing** (`instruction_parser.py`): sends the section outline
  (id + title + short preview) and the instructions to Claude with a forced
  tool call (`submit_edit_plan`), so the response is always well-formed JSON,
  never free text to re-interpret. The model also returns confidence and
  candidate section ids directly — see the note in that file about why this
  skips the separate embeddings-matching step from the original architecture
  doc.

- **Deletion** (`pdf_mutator.py`): real PDF redaction — the section's actual
  text spans are blacked out and removed via `apply_redactions()`. If a
  deletion empties a page completely, that page is dropped.

- **Addition** (append / insert): new content is rendered onto a freshly
  created page sized to match the document, then spliced in immediately
  after the target section via `move_page`. This avoids needing a full reflow
  engine, at the cost of additions always starting on their own page rather
  than flowing into existing whitespace.

- **Diff preview**: a plain-text line-level diff (`difflib`) of the
  extracted text before/after. Returned as plain text, not HTML — the
  frontend currently renders these fields as plain text, not via
  `dangerouslySetInnerHTML`.

## Known v1 limitations (intentional, for this pass)

- **In-memory only.** Jobs and download tokens vanish on restart. Fine for
  this pass per your call — swap `store.py` for SQLite/Postgres when needed,
  the rest of the app talks to it through a small functional interface
  (`create_job`, `get_job`, `issue_download_token`, `resolve_token`) so that's
  a contained change.
- **No semantic embeddings step** — Claude resolves section references
  directly from the outline. Worth revisiting if you test against documents
  with many similarly-named sections.
- **Long additions don't auto-paginate** — PyMuPDF's `insert_textbox` doesn't
  return unfit overflow text, so a very long appended paragraph could run off
  the bottom of its new page. Fine for paragraph-length additions; flagged
  for whoever extends this.
- **No persistence of the original PDF beyond the job's lifetime** — nothing
  is written to disk; everything lives in memory as bytes.

## Wiring up the frontend

The frontend's `src/api/client.ts` currently contains a hardcoded mock. To
point it at this backend: replace `analyzeInstructions` / `applyEditPlan`
with real `fetch` calls to `http://localhost:8000/api/analyze` (as
`FormData`) and `/api/jobs/{jobId}/apply`, respectively — the response
shapes already match `types.ts` exactly, so no frontend type changes should
be needed.
