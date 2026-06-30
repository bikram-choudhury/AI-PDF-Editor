from typing import List, Literal, Optional

from pydantic import BaseModel

OperationType = Literal["delete_section", "append_to_section", "insert_new_section"]


class EditOperation(BaseModel):
    id: str
    op: OperationType
    targetLabel: str
    contentPreview: Optional[str] = None
    confidence: float
    needsConfirmation: bool
    ambiguityNote: Optional[str] = None


class AnalyzeResponse(BaseModel):
    jobId: str
    sourceFileName: str
    operations: List[EditOperation]


class ApplyResponse(BaseModel):
    jobId: str
    downloadUrl: str
    downloadFileName: str
    diffHtmlBefore: str
    diffHtmlAfter: str
    expiresInSeconds: int
