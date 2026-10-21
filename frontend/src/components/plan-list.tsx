"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { ConfirmButton } from "@/components/confirm-button";
import { LeaveSection } from "@/components/leave-section";
import { StatusBadge } from "@/components/status-badge";
import { TEXT_LINK } from "@/components/styles";
import {
  type PlanList as Plans,
  deletePlan,
  messageOf,
  requestJson,
} from "@/lib/api/client";
import {
  CONFIRM_DELETE_LABEL,
  DELETE_PLAN_NOTE,
  deletable,
  deletePlanLabel,
  deletedPlanLabel,
  semesterLabel,
} from "@/lib/labels";

const CREATED_AT = new Intl.DateTimeFormat("ja-JP", {
  timeZone: "Asia/Tokyo",
  dateStyle: "medium",
  timeStyle: "short",
});

const ROW_STAGGER_MS = 60;
const STAGGERED_ROWS = 10;

export function PlanList() {
  const [plans, setPlans] = useState<Plans>();
  const [error, setError] = useState<string>();
  const [reloads, setReloads] = useState(0);
  const [deleted, setDeleted] = useState<string>();
  const notice = useRef<HTMLParagraphElement>(null);

  useEffect(() => {
    let active = true;
    requestJson<Plans>("/api/plans")
      .then((answer) => {
        if (active) {
          setPlans(answer);
        }
      })
      .catch((caught: unknown) => {
        if (active) {
          setError(messageOf(caught));
        }
      });
    return () => {
      active = false;
    };
  }, [reloads]);

  useEffect(() => {
    if (deleted) {
      notice.current?.focus();
    }
  }, [deleted]);

  if (error) {
    return (
      <p role="alert" className="text-sm text-danger">
        一覧を読み込めませんでした: {error}
      </p>
    );
  }
  if (!plans) {
    return <p className="text-sm text-sub">読み込んでいます</p>;
  }
  async function remove(id: string, occupation: string) {
    await deletePlan(id);
    setDeleted(deletedPlanLabel(occupation));
    setReloads((current) => current + 1);
  }

  return (
    <div className="grid gap-10">
      <p
        ref={notice}
        role="status"
        tabIndex={-1}
        className="text-sm text-sub empty:hidden"
      >
        {deleted}
      </p>
      {plans.plans.length === 0 ? (
        <p className="text-sm text-sub">
          まだ道標がありません。
          <Link href="/" className={TEXT_LINK}>
            道標を作る
          </Link>
        </p>
      ) : (
        <ul className="grid gap-3">
          {plans.plans.map((plan, index) => (
            <li
              key={plan.id}
              style={{
                animationDelay: `${Math.min(index, STAGGERED_ROWS) * ROW_STAGGER_MS}ms`,
              }}
              className="flex flex-wrap items-center gap-2 motion-safe:animate-rise"
            >
              <Link
                href={`/plans/${plan.id}`}
                className="group flex min-w-0 flex-1 basis-64 flex-wrap items-center justify-between gap-3 rounded-lg border border-l-4 border-line border-l-route bg-sheet px-5 py-4 shadow-paper transition-colors hover:border-l-pillar"
              >
                <span className="grid min-w-0 gap-0.5">
                  <span className="truncate font-serif text-lg font-bold">
                    {plan.occupation}
                  </span>
                  <span className="text-xs text-sub">
                    {semesterLabel(plan.grade, plan.term)}から ・{" "}
                    {CREATED_AT.format(new Date(plan.created_at))}
                  </span>
                </span>
                <span className="flex items-center gap-3">
                  <StatusBadge status={plan.status} />
                  <span
                    aria-hidden
                    className="text-route transition-transform group-hover:translate-x-1"
                  >
                    →
                  </span>
                </span>
              </Link>
              {deletable(plan.status) && (
                <ConfirmButton
                  label="消す"
                  name={deletePlanLabel(plan.occupation)}
                  note={DELETE_PLAN_NOTE}
                  confirmLabel={CONFIRM_DELETE_LABEL}
                  onConfirm={() => remove(plan.id, plan.occupation)}
                />
              )}
            </li>
          ))}
        </ul>
      )}
      <LeaveSection plans={plans.total} />
    </div>
  );
}
