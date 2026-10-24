"use client";

import { type ReactNode, useEffect, useState } from "react";

import { DestinationPlate } from "@/components/destination-plate";
import { Signpost } from "@/components/signpost";
import { PHRASE_WRAP } from "@/components/styles";
import type { Plan } from "@/lib/api/client";
import { STAGE_LABELS, WAITING_LABEL, semesterLabel } from "@/lib/labels";
import {
  type Step,
  type StepState,
  progressSteps,
  travelled,
} from "@/lib/progress";

const TICK_MS = 1_000;
const BLINKING_DOTS = [0, 1, 2];

const LABEL_STYLES: Record<StepState, string> = {
  done: "text-ink",
  now: "font-bold text-ink",
  later: "text-sub",
};

export function PlanProgress({
  plan,
  stalled,
}: {
  plan: Plan;
  stalled?: ReactNode;
}) {
  const { conditions } = plan;
  const [startedAt] = useState(Date.now);
  const steps = progressSteps(plan.status, plan.stage);
  const current = steps.find((step) => step.state === "now");
  return (
    <section className="mx-auto grid max-w-xl gap-6 rounded-lg border border-line bg-sheet p-6 shadow-paper motion-safe:animate-rise sm:p-8">
      <div className="flex items-start justify-between gap-4">
        <div className="grid min-w-0 gap-1.5">
          <DestinationPlate destination={conditions.occupation} />
          <h1
            className={`font-serif text-2xl font-extrabold text-balance ${PHRASE_WRAP}`}
          >
            <span className="sr-only">{conditions.occupation}への</span>
            道標を作っています
          </h1>
          <p className="text-sm text-sub">
            {semesterLabel(conditions.grade, conditions.term)}
            から卒業までを組みます。
          </p>
        </div>
        <Signpost
          from={`${conditions.grade} 回生`}
          className="w-14 shrink-0 origin-bottom text-ink motion-safe:animate-sway sm:w-16"
        />
      </div>
      {plan.status === "pending" && (
        <p aria-hidden className="flex items-center gap-2.5 text-sm font-bold">
          <span
            aria-hidden
            className="size-3.5 rounded-full border-[3px] border-pillar motion-safe:animate-beacon"
          />
          {WAITING_LABEL}
        </p>
      )}
      <StepLine steps={steps} />
      <div className="grid gap-3">
        <div aria-live="polite">
          <p className="sr-only">
            {current ? STAGE_LABELS[current.stage] : WAITING_LABEL}
          </p>
          {stalled}
        </div>
        {!stalled && <WaitedTime since={startedAt} />}
      </div>
    </section>
  );
}

function StepLine({ steps }: { steps: Step[] }) {
  return (
    <div className="relative">
      <span
        aria-hidden
        className="absolute inset-y-5.5 left-[8.5px] w-[3px] rounded-full bg-[repeating-linear-gradient(to_bottom,var(--line)_0_6px,transparent_6px_12px)] motion-safe:animate-march"
      />
      <span
        aria-hidden
        style={{ height: `calc((100% - 2.75rem) * ${travelled(steps)})` }}
        className="absolute top-5.5 left-[8.5px] w-[3px] rounded-full bg-route transition-[height] duration-700 ease-out"
      />
      <ol className="relative grid">
        {steps.map((step) => (
          <li
            key={step.stage}
            aria-current={step.state === "now" ? "step" : undefined}
            className={`relative flex h-11 items-center gap-1.5 pl-9 text-sm transition-colors duration-500 ${LABEL_STYLES[step.state]}`}
          >
            <StationDot state={step.state} />
            {STAGE_LABELS[step.stage]}
            {step.state === "now" && (
              <span aria-hidden className="flex gap-1">
                {BLINKING_DOTS.map((dot) => (
                  <span
                    key={dot}
                    style={{ animationDelay: `${dot * 0.2}s` }}
                    className="size-1 rounded-full bg-pillar motion-safe:animate-blink"
                  />
                ))}
              </span>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}

function StationDot({ state }: { state: StepState }) {
  const place =
    "absolute top-1/2 left-0 -mt-2.5 grid size-5 place-items-center rounded-full";
  if (state === "done") {
    return (
      <span
        aria-hidden
        className={`${place} bg-route text-paper motion-safe:animate-pop`}
      >
        <svg viewBox="0 0 12 12" className="size-3">
          <path
            d="M2.5 6.5l2.2 2.2L9.5 3.8"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </span>
    );
  }
  if (state === "now") {
    return (
      <span
        aria-hidden
        className={`${place} border-[3px] border-pillar bg-sheet motion-safe:animate-beacon`}
      >
        <span className="size-1.5 rounded-full bg-pillar" />
      </span>
    );
  }
  return (
    <span
      aria-hidden
      className={`${place} border-[3px] border-line bg-sheet`}
    />
  );
}

function WaitedTime({ since }: { since: number }) {
  const [now, setNow] = useState(Date.now);
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), TICK_MS);
    return () => clearInterval(timer);
  }, []);
  return (
    <p className="text-xs text-sub">
      <span className="tabular-nums">
        待ち時間 {Math.floor((now - since) / TICK_MS)} 秒
      </span>{" "}
      ・ ふだん 10〜30 秒で終わります。このページを開いたままお待ちください。
    </p>
  );
}
