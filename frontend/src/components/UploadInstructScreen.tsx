import { useState } from "react";
import { FileDropzone } from "./FileDropzone";

interface UploadInstructScreenProps {
  onSubmit: (file: File, instructions: string) => void;
  isAnalyzing: boolean;
}

export function UploadInstructScreen({ onSubmit, isAnalyzing }: UploadInstructScreenProps) {
  const [file, setFile] = useState<File | null>(null);
  const [instructions, setInstructions] = useState("");

  const canSubmit = file !== null && instructions.trim().length > 0 && !isAnalyzing;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <label className="mb-2 block text-sm font-medium text-ink">PDF to edit</label>
        <FileDropzone file={file} onFileSelected={setFile} />
      </div>

      <div>
        <label htmlFor="instructions" className="mb-2 block text-sm font-medium text-ink">
          Instructions
        </label>
        <textarea
          id="instructions"
          rows={5}
          value={instructions}
          onChange={(e) => setInstructions(e.target.value)}
          placeholder='e.g. "Remove the Termination Clause section, add a paragraph about refunds under Payment Terms, and insert a new Privacy Policy section at the end."'
          className="w-full resize-none rounded-lg border border-rule bg-paper-raised px-3 py-2.5 text-sm text-ink placeholder:text-ink-tertiary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
        />
        <p className="mt-1.5 text-xs text-ink-tertiary">
          Describe removals, additions, or new sections in plain language.
        </p>
      </div>

      <p className="text-xs text-ink-tertiary">
        Output is always written to a new file — your original PDF is never modified.
      </p>

      <button
        disabled={!canSubmit}
        onClick={() => file && onSubmit(file, instructions)}
        className="self-start rounded-md bg-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-strong disabled:cursor-not-allowed disabled:bg-rule-strong disabled:text-ink-tertiary"
      >
        {isAnalyzing ? "Analyzing…" : "Analyze instructions"}
      </button>
    </div>
  );
}
