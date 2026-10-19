import type { PlanStage, PlanStatus } from "@/lib/api/client";
import { STAGE_LABELS, WAITING_LABEL } from "@/lib/labels";
import { type StepState, progressSteps } from "@/lib/progress";

const STEP_STYLES: Record<StepState, string> = {
  done: "text-ink before:border-route before:bg-route",
  now: "font-bold text-ink before:border-pillar before:bg-sheet motion-safe:before:animate-beacon",
  later: "text-sub before:border-line before:bg-sheet",
};

export function ProgressSteps({
  status,
  stage,
}: {
  status: PlanStatus;
  stage: PlanStage | null;
}) {
  return (
    <div className="grid gap-4">
      {status === "pending" && (
        <p className="flex items-center gap-2.5 text-sm font-bold">
          <span
            aria-hidden
            className="size-3.5 rounded-full border-[3px] border-pillar motion-safe:animate-beacon"
          />
          {WAITING_LABEL}
        </p>
      )}
      <ol className="relative grid gap-3 pl-8 before:absolute before:inset-y-1.5 before:left-[9px] before:w-[3px] before:rounded-full before:bg-line">
        {progressSteps(status, stage).map((step) => (
          <li
            key={step.stage}
            aria-current={step.state === "now" ? "step" : undefined}
            className={`relative text-sm transition-colors before:absolute before:top-[5px] before:-left-[27px] before:size-[15px] before:rounded-full before:border-[3px] before:transition-colors ${STEP_STYLES[step.state]}`}
          >
            {STAGE_LABELS[step.stage]}
          </li>
        ))}
      </ol>
    </div>
  );
}
