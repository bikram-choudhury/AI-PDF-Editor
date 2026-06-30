import { useMutation } from "@tanstack/react-query";
import { analyzeInstructions, applyEditPlan } from "../api/client";
import type { AnalyzeRequest } from "../types";

export function useAnalyzeInstructions() {
  return useMutation({
    mutationFn: (req: AnalyzeRequest) => analyzeInstructions(req),
  });
}

export function useApplyEditPlan() {
  return useMutation({
    mutationFn: (jobId: string) => applyEditPlan(jobId),
  });
}
