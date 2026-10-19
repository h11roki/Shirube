import type { PlanStage, PlanStatus } from "@/lib/api/client";

const STAGES: PlanStage[] = ["analyzing", "searching", "selecting", "placing"];

export type StepState = "done" | "now" | "later";

export type Step = { stage: PlanStage; state: StepState };

export function progressSteps(
  status: PlanStatus,
  stage: PlanStage | null,
): Step[] {
  const current =
    status === "running" ? STAGES.indexOf(stage ?? STAGES[0]) : -1;
  return STAGES.map((each, index) => ({
    stage: each,
    state: index < current ? "done" : index === current ? "now" : "later",
  }));
}

export function travelled(steps: Step[]): number {
  const current = steps.findIndex((step) => step.state === "now");
  return current <= 0 ? 0 : current / (steps.length - 1);
}
