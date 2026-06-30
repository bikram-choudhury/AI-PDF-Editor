import type { EditOperation } from "../types";

const OP_LABEL: Record<EditOperation["op"], string> = {
  delete_section: "Delete",
  append_to_section: "Append",
  insert_new_section: "Insert",
};

const OP_STYLES: Record<EditOperation["op"], { bar: string; badge: string; text: string }> = {
  delete_section: {
    bar: "bg-op-delete",
    badge: "bg-op-delete-soft text-op-delete",
    text: "text-ink",
  },
  append_to_section: {
    bar: "bg-op-append",
    badge: "bg-op-append-soft text-op-append",
    text: "text-ink",
  },
  insert_new_section: {
    bar: "bg-op-warn",
    badge: "bg-op-warn-soft text-op-warn",
    text: "text-ink",
  },
};

interface EditPlanRowProps {
  operation: EditOperation;
}

export function EditPlanRow({ operation }: EditPlanRowProps) {
  const styles = OP_STYLES[operation.op];
  const flagged = operation.needsConfirmation;

  return (
    <div
      className={`flex gap-3 rounded-md border py-2.5 pr-3 ${
        flagged ? "border-op-warn/40 bg-op-warn-soft/40" : "border-rule"
      }`}
    >
      <span className={`w-1 shrink-0 rounded-full ${styles.bar}`} aria-hidden="true" />
      <div className="flex min-w-0 flex-1 flex-col gap-1 py-0.5">
        <div className="flex items-center gap-2">
          <span
            className={`shrink-0 rounded px-2 py-0.5 text-xs font-medium ${styles.badge}`}
          >
            {OP_LABEL[operation.op]}
          </span>
          <span className={`truncate text-sm ${styles.text}`}>{operation.targetLabel}</span>
        </div>
        {operation.contentPreview && (
          <p className="truncate text-xs text-ink-tertiary">{operation.contentPreview}</p>
        )}
        {flagged && operation.ambiguityNote && (
          <p className="text-xs text-op-warn">{operation.ambiguityNote}</p>
        )}
      </div>
      <span className="self-center pr-1 text-xs tabular-nums text-ink-tertiary">
        {Math.round(operation.confidence * 100)}%
      </span>
    </div>
  );
}
