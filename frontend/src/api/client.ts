import type { AnalyzeRequest, AnalyzeResponse, ApplyResponse, EditOperation } from "../types";

function delay<T>(value: T, ms: number): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

function id() {
  return Math.random().toString(36).slice(2, 10);
}

/**
 * POST /api/analyze
 * In production this sends { file, instructions } as multipart form data
 * and the backend returns the parsed edit plan (see plan doc section 2).
 */
export async function analyzeInstructions({ file, instructions }: AnalyzeRequest): Promise<AnalyzeResponse> {
  const operations: EditOperation[] = [];

  const lower = instructions.toLowerCase();

  if (lower.includes("remove") || lower.includes("delete")) {
    operations.push({
      id: id(),
      op: "delete_section",
      targetLabel: 'Section 3 — "Termination Clause"',
      confidence: 0.94,
      needsConfirmation: false,
    });
  }
  if (lower.includes("add") || lower.includes("refund")) {
    operations.push({
      id: id(),
      op: "append_to_section",
      targetLabel: 'Add refunds paragraph to "Payment Terms"',
      contentPreview: "Refunds will be processed within 14 business days of a valid cancellation request.",
      confidence: 0.88,
      needsConfirmation: false,
    });
  }
  if (lower.includes("insert") || lower.includes("new section") || lower.includes("privacy")) {
    operations.push({
      id: id(),
      op: "insert_new_section",
      targetLabel: 'New "Privacy Policy" section',
      confidence: 0.52,
      needsConfirmation: true,
      ambiguityNote: "2 possible insert points — end of document, or after Section 4",
    });
  }

  if (operations.length === 0) {
    operations.push({
      id: id(),
      op: "append_to_section",
      targetLabel: "Could not confidently match a section",
      confidence: 0.31,
      needsConfirmation: true,
      ambiguityNote: "Try referencing a section by name",
    });
  }

  return delay(
    {
      jobId: id(),
      sourceFileName: file.name,
      operations,
    },
    900,
  );
}

/**
 * POST /api/jobs/{jobId}/apply
 * In production this applies the confirmed edit plan server-side and
 * returns a signed, time-limited download URL (see plan doc section 6).
 */
export async function applyEditPlan(jobId: string): Promise<ApplyResponse> {
  return delay(
    {
      jobId,
      downloadUrl: "https://example-storage.local/signed/updated_contract.pdf?sig=mock",
      downloadFileName: "updated_contract.pdf",
      diffHtmlBefore: "Original document content would render here.",
      diffHtmlAfter: "Updated document content, with additions and removals highlighted, renders here.",
      expiresInSeconds: 1800,
    },
    1100,
  );
}
