import { useState } from "react";
import { UploadInstructScreen } from "./components/UploadInstructScreen";
import { ReviewDownloadScreen } from "./components/ReviewDownloadScreen";
import { useAnalyzeInstructions, useApplyEditPlan } from "./hooks/useEditPlan";
import type { AnalyzeResponse } from "./types";

type Step = 1 | 2;

const STEPS: { step: Step; label: string }[] = [
  { step: 1, label: "Upload & instruct" },
  { step: 2, label: "Review & download" },
];

function App() {
  const [step, setStep] = useState<Step>(1);
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);

  const analyzeMutation = useAnalyzeInstructions();
  const applyMutation = useApplyEditPlan();

  const handleSubmit = async (file: File, instructions: string) => {
    const result = await analyzeMutation.mutateAsync({ file, instructions });
    setAnalysis(result);
    setStep(2);
  };

  const handleBack = () => {
    setStep(1);
    setAnalysis(null);
    analyzeMutation.reset();
    applyMutation.reset();
  };

  const handleConfirm = () => {
    if (analysis) applyMutation.mutate(analysis.jobId);
  };

  return (
    <div className="min-h-screen bg-paper">
      <div className="mx-auto max-w-xl px-6 py-12">
        <header className="mb-8">
          <p className="font-mono text-xs tracking-wide text-ink-tertiary uppercase">
            Redraft
          </p>
          <h1 className="mt-1 font-display text-2xl text-ink">
            Instruction-driven PDF editing
          </h1>
        </header>

        <ol className="mb-8 flex items-center gap-6">
          {STEPS.map(({ step: s, label }) => (
            <li key={s} className="flex items-center gap-2">
              <span
                className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-medium ${
                  step === s
                    ? "bg-accent text-white"
                    : step > s
                      ? "bg-accent-soft text-accent"
                      : "bg-rule text-ink-tertiary"
                }`}
              >
                {s}
              </span>
              <span
                className={`text-sm ${step === s ? "text-ink" : "text-ink-tertiary"}`}
              >
                {label}
              </span>
            </li>
          ))}
        </ol>

        <main className="rounded-xl border border-rule bg-paper-raised p-6 shadow-sm">
          {step === 1 && (
            <UploadInstructScreen
              onSubmit={handleSubmit}
              isAnalyzing={analyzeMutation.isPending}
            />
          )}
          {step === 2 && analysis && (
            <ReviewDownloadScreen
              analysis={analysis}
              onBack={handleBack}
              onConfirm={handleConfirm}
              isApplying={applyMutation.isPending}
              result={applyMutation.data ?? null}
            />
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
