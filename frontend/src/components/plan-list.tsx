"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { StatusBadge } from "@/components/status-badge";
import { type PlanList as Plans, requestJson } from "@/lib/api/client";
import { semesterLabel } from "@/lib/labels";

const CREATED_AT = new Intl.DateTimeFormat("ja-JP", {
  timeZone: "Asia/Tokyo",
  dateStyle: "medium",
  timeStyle: "short",
});

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
          setError(
            caught instanceof Error ? caught.message : "読み込めませんでした",
          );
        }
      });
    return () => {
      active = false;
    };
  }, []);

  if (error) {
    return (
      <p role="alert" className="text-sm text-red-700">
        一覧を読み込めませんでした: {error}
      </p>
    );
  }
  if (!plans) {
    return <p className="text-sm text-stone-500">読み込んでいます</p>;
  }
  if (plans.plans.length === 0) {
    return (
      <p className="text-sm text-stone-600">
        まだ道標がありません。
        <Link href="/" className="text-teal-800 underline">
          道標を作る
        </Link>
      </p>
    );
  }
  return (
    <ul className="divide-y divide-stone-200 overflow-hidden rounded-xl border border-stone-200 bg-white">
      {plans.plans.map((plan) => (
        <li key={plan.id}>
          <Link
            href={`/plans/${plan.id}`}
            className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 hover:bg-stone-50"
          >
            <span className="min-w-0">
              <span className="block truncate font-medium">
                {plan.occupation}
              </span>
              <span className="text-xs text-stone-500">
                {semesterLabel(plan.grade, plan.term)}から・
                {CREATED_AT.format(new Date(plan.created_at))}
              </span>
            </span>
            <StatusBadge status={plan.status} />
          </Link>
        </li>
      ))}
    </ul>
  );
}
