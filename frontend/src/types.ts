export type OperationType = "delete_section" | "append_to_section" | "insert_new_section";

export interface EditOperation {
  id: string;
  op: OperationType;
  targetLabel: string;
  contentPreview?: string;
  confidence: number;
  needsConfirmation: boolean;
  ambiguityNote?: string;
}

export interface AnalyzeRequest {
  file: File;
  instructions: string;
}

export interface AnalyzeResponse {
  jobId: string;
  sourceFileName: string;
  operations: EditOperation[];
}

export interface ApplyResponse {
  jobId: string;
  downloadUrl: string;
  downloadFileName: string;
  diffHtmlBefore: string;
  diffHtmlAfter: string;
  expiresInSeconds: number;
}
