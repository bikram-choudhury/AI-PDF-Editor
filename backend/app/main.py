from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from . import config, store
from .diffing import extract_full_text, summarize_diff
from .instruction_parser import parse_instructions
from .models import AnalyzeResponse, ApplyResponse, EditOperation
from .pdf_mutator import apply_edit_plan
from .pdf_structure import extract_sections

app = FastAPI(title="Redraft PDF Editor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(file: UploadFile = File(...), instructions: str = Form(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(400, "Only PDF files are supported.")

    pdf_bytes = file.file.read()
    if not pdf_bytes:
        raise HTTPException(400, "Uploaded file is empty.")

    if not instructions.strip():
        raise HTTPException(400, "Instructions cannot be empty.")

    sections = extract_sections(pdf_bytes)
    if not sections:
        raise HTTPException(422, "Could not detect any readable text or sections in this PDF.")

    try:
        operations = parse_instructions(sections, instructions)
    except RuntimeError as exc:
        raise HTTPException(502, str(exc))

    if not operations:
        raise HTTPException(422, "Could not parse any edit operations from these instructions.")

    job = store.create_job(file.filename or "document.pdf", pdf_bytes, sections, operations)

    return AnalyzeResponse(
        jobId=job.job_id,
        sourceFileName=job.source_filename,
        operations=[_to_public_operation(op) for op in operations],
    )


@app.post("/api/jobs/{job_id}/apply", response_model=ApplyResponse)
def apply(job_id: str):
    job = store.get_job(job_id)
    if job is None:
        raise HTTPException(404, "Job not found. It may have expired or the server restarted.")

    if any(op.needs_confirmation for op in job.operations):
        raise HTTPException(409, "This edit plan has unresolved operations and cannot be applied yet.")

    updated_bytes = apply_edit_plan(job.original_pdf_bytes, job.sections, job.operations)
    job.applied_pdf_bytes = updated_bytes

    before_text = extract_full_text(job.original_pdf_bytes)
    after_text = extract_full_text(updated_bytes)
    diff_before, diff_after = summarize_diff(before_text, after_text)

    token = store.issue_download_token(job_id, config.DOWNLOAD_TTL_SECONDS)
    download_filename = _derive_output_filename(job.source_filename)

    return ApplyResponse(
        jobId=job_id,
        downloadUrl=f"{config.PUBLIC_BASE_URL}/api/download/{token}",
        downloadFileName=download_filename,
        diffHtmlBefore=diff_before,
        diffHtmlAfter=diff_after,
        expiresInSeconds=config.DOWNLOAD_TTL_SECONDS,
    )


@app.get("/api/download/{token}")
def download(token: str):
    job = store.resolve_token(token)
    if job is None or job.applied_pdf_bytes is None:
        raise HTTPException(404, "This download link is invalid or has expired.")

    filename = _derive_output_filename(job.source_filename)
    return Response(
        content=job.applied_pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _to_public_operation(op: store.ParsedOperation) -> EditOperation:
    return EditOperation(
        id=op.id,
        op=op.op,
        targetLabel=op.label,
        contentPreview=(op.content[:160] if op.content else None),
        confidence=op.confidence,
        needsConfirmation=op.needs_confirmation,
        ambiguityNote=op.ambiguity_note,
    )


def _derive_output_filename(original_filename: str) -> str:
    base = original_filename.rsplit(".", 1)[0] if "." in original_filename else original_filename
    return f"{base}_updated.pdf"
