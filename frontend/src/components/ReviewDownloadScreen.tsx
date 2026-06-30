import { useState } from "react";
import type { AnalyzeResponse, ApplyResponse } from "../types";
import { EditPlanRow } from "./EditPlanRow";

interface ReviewDownloadScreenProps {
  analysis: AnalyzeResponse;
  onBack: () => void;
  onConfirm: () => void;
  isApplying: boolean;
  result: ApplyResponse | null;
}

export function ReviewDownloadScreen({
  analysis,
  onBack,
  onConfirm,
  isApplying,
  result,
}: ReviewDownloadScreenProps) {
  const [previewMode, setPreviewMode] = useState<"before" | "after">("after");
  const hasUnresolved = analysis.operations.some((op) => op.needsConfirmation);

  return (
    <div className="flex flex-col gap-5">
      <div>
        <p className="mb-2 text-xs font-medium tracking-wide text-ink-tertiary uppercase">
          Parsed edit plan · {analysis.sourceFileName}
        </p>
        <div className="flex flex-col gap-2">
          {analysis.operations.map((op) => (
            <EditPlanRow key={op.id} operation={op} />
          ))}
        </div>
        {hasUnresolved && (
          <p className="mt-2 text-xs text-op-warn">
            One or more changes need confirmation before this plan can be applied.
          </p>
        )}
      </div>

      {!result && (
        <div className="flex gap-2">
          <button
            onClick={onBack}
            className="rounded-md border border-rule px-4 py-2 text-sm font-medium text-ink-secondary transition-colors hover:bg-paper-raised"
          >
            Edit instructions
          </button>
          <button
            disabled={hasUnresolved || isApplying}
            onClick={onConfirm}
            className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-strong disabled:cursor-not-allowed disabled:bg-rule-strong disabled:text-ink-tertiary"
          >
            {isApplying ? "Applying…" : "Confirm & apply"}
          </button>
        </div>
      )}

      {result && (
        <div className="flex flex-col gap-3 border-t border-rule pt-4">
          <p className="text-xs font-medium tracking-wide text-ink-tertiary uppercase">
            After confirm
          </p>

          <div className="flex gap-1.5">
            <button
              onClick={() => setPreviewMode("before")}
              className={`flex-1 rounded-md border px-3 py-1.5 text-sm transition-colors ${
                previewMode === "before"
                  ? "border-accent text-accent"
                  : "border-rule text-ink-secondary"
              }`}
            >
              Before
            </button>
            <button
              onClick={() => setPreviewMode("after")}
              className={`flex-1 rounded-md border px-3 py-1.5 text-sm transition-colors ${
                previewMode === "after"
                  ? "border-accent text-accent"
                  : "border-rule text-ink-secondary"
              }`}
            >
              After (diff highlighted)
            </button>
          </div>

          <div className="rounded-md border border-rule bg-paper-raised px-3 py-3 text-sm text-ink-secondary">
            {previewMode === "before" ? result.diffHtmlBefore : result.diffHtmlAfter}
          </div>

          <div className="flex items-center justify-between border-t border-rule pt-3">
            <div className="min-w-0">
              <p className="truncate font-mono text-sm text-ink">{result.downloadFileName}</p>
              <p className="text-xs text-ink-tertiary">
                Expires in {Math.round(result.expiresInSeconds / 60)} min
              </p>
            </div>
            <a
              href={result.downloadUrl}
              download={result.downloadFileName}
              className="shrink-0 rounded-md bg-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-strong"
            >
              Download
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
