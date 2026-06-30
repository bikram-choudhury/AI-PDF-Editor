import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .pdf_structure import Section


@dataclass
class ParsedOperation:
    """Server-side representation of one edit-plan operation. Carries the
    extra fields (target_section_id, raw content) needed to actually apply
    the edit, beyond what's exposed to the frontend via EditOperation."""

    id: str
    op: str
    target_section_id: Optional[str]
    candidate_section_ids: List[str]
    new_title: Optional[str]
    content: Optional[str]
    confidence: float
    needs_confirmation: bool
    label: str
    ambiguity_note: Optional[str]


@dataclass
class JobRecord:
    job_id: str
    source_filename: str
    original_pdf_bytes: bytes
    sections: List[Section]
    operations: List[ParsedOperation]
    applied_pdf_bytes: Optional[bytes] = None
    download_token: Optional[str] = None
    token_expires_at: Optional[float] = None


_lock = threading.Lock()
_jobs: Dict[str, JobRecord] = {}
_tokens: Dict[str, str] = {}  # download token -> job_id


def create_job(
    source_filename: str,
    original_pdf_bytes: bytes,
    sections: List[Section],
    operations: List[ParsedOperation],
) -> JobRecord:
    job_id = str(uuid.uuid4())
    record = JobRecord(
        job_id=job_id,
        source_filename=source_filename,
        original_pdf_bytes=original_pdf_bytes,
        sections=sections,
        operations=operations,
    )
    with _lock:
        _jobs[job_id] = record
    return record


def get_job(job_id: str) -> Optional[JobRecord]:
    with _lock:
        return _jobs.get(job_id)


def issue_download_token(job_id: str, ttl_seconds: int) -> str:
    token = str(uuid.uuid4())
    with _lock:
        _tokens[token] = job_id
        job = _jobs[job_id]
        job.download_token = token
        job.token_expires_at = time.time() + ttl_seconds
    return token


def resolve_token(token: str) -> Optional[JobRecord]:
    with _lock:
        job_id = _tokens.get(token)
        if not job_id:
            return None
        job = _jobs.get(job_id)
        if job is None or job.token_expires_at is None:
            return None
        if time.time() > job.token_expires_at:
            return None
        return job
