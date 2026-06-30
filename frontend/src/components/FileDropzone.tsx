import { useCallback, useRef, useState } from "react";

interface FileDropzoneProps {
  file: File | null;
  onFileSelected: (file: File) => void;
}

export function FileDropzone({ file, onFileSelected }: FileDropzoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(
    (files: FileList | null) => {
      const candidate = files?.[0];
      if (candidate && candidate.type === "application/pdf") {
        onFileSelected(candidate);
      }
    },
    [onFileSelected],
  );

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragOver(true);
      }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragOver(false);
        handleFiles(e.dataTransfer.files);
      }}
      onClick={() => inputRef.current?.click()}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
      }}
      className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed px-6 py-10 text-center transition-colors ${
        isDragOver
          ? "border-accent bg-accent-soft"
          : "border-rule-strong hover:border-ink-tertiary"
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
      {file ? (
        <>
          <span className="font-mono text-sm text-ink">{file.name}</span>
          <span className="text-xs text-ink-tertiary">
            {(file.size / 1024).toFixed(0)} KB · click to replace
          </span>
        </>
      ) : (
        <>
          <span className="text-sm text-ink-secondary">
            Drag a PDF here, or click to browse
          </span>
          <span className="text-xs text-ink-tertiary">.pdf only</span>
        </>
      )}
    </div>
  );
}
