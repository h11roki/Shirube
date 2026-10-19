"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { StatusBadge } from "@/components/status-badge";
import {
  type PlanList as Plans,
  messageOf,
  requestJson,
} from "@/lib/api/client";
import { semesterLabel } from "@/lib/labels";

const CREATED_AT = new Intl.DateTimeFormat("ja-JP", {
  timeZone: "Asia/Tokyo",
  dateStyle: "medium",
  timeStyle: "short",
});

const STAGGER_MS = 60;
const STAGGERED_ROWS = 10;

export function PlanList() {
  const [plans, setPlans] = useState<Plans>();
  const [error, setError] = useState<string>();

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
  }, []);

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
  if (plans.plans.length === 0) {
    return (
      <p className="text-sm text-sub">
        まだ道標がありません。
        <Link href="/" className="text-route underline underline-offset-4">
          道標を作る
        </Link>
      </p>
    );
  }
  return (
    <ul className="grid gap-3">
      {plans.plans.map((plan, index) => (
        <li
          key={plan.id}
          style={{
            animationDelay: `${Math.min(index, STAGGERED_ROWS) * STAGGER_MS}ms`,
          }}
          className="motion-safe:animate-rise"
        >
          <Link
            href={`/plans/${plan.id}`}
            className="group flex flex-wrap items-center justify-between gap-3 rounded-lg border border-l-4 border-line border-l-route bg-sheet px-5 py-4 shadow-paper transition-colors hover:border-l-pillar"
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
        </li>
      ))}
    </ul>
  );
}
