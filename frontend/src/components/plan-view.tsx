"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";

import { PlanResultView } from "@/components/plan-result";
import { StatusBadge } from "@/components/status-badge";
import { type Plan, requestJson } from "@/lib/api/client";
import { semesterLabel } from "@/lib/labels";
import { POLL_INTERVAL_MS, type Watch, watchState } from "@/lib/polling";

export function PlanView() {
  const { id } = useParams<{ id: string }>();
  const [plan, setPlan] = useState<Plan>();
  const [watch, setWatch] = useState<Watch>("waiting");
  const [error, setError] = useState<string>();
  const [round, setRound] = useState(0);

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const startedAt = Date.now();
    async function poll() {
      try {
        const latest = await requestJson<Plan>(
          `/api/plans/${encodeURIComponent(id)}`,
        );
        if (!active) {
          return;
        }
        const state = watchState(latest.status, Date.now() - startedAt);
        setPlan(latest);
        setWatch(state);
        setError(undefined);
        if (state === "waiting") {
          timer = setTimeout(poll, POLL_INTERVAL_MS);
        }
      } catch (caught) {
        if (active) {
          setError(
            caught instanceof Error ? caught.message : "読み込めませんでした",
          );
        }
      }
    }
    void poll();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [id, round]);

  function retry() {
    setError(undefined);
    setWatch("waiting");
    setRound((current) => current + 1);
  }

  if (error) {
    return (
      <Notice title="道標を読み込めませんでした">
        <p>{error}</p>
        <RetryButton onClick={retry} />
      </Notice>
    );
  }
  if (!plan) {
    return <p className="text-sm text-stone-500">読み込んでいます</p>;
  }
  if (plan.status === "succeeded" && plan.result) {
    return <PlanResultView plan={plan} result={plan.result} />;
  }
  if (plan.status === "failed") {
    return (
      <Notice title="道標を作れませんでした">
        <p>{plan.failure}</p>
        <Link href="/" className="text-teal-800 underline">
          もう一度作る
        </Link>
      </Notice>
    );
  }
  const { conditions } = plan;
  return (
    <section
      aria-live="polite"
      className="space-y-3 rounded-xl border border-stone-200 bg-white p-6 shadow-sm"
    >
      <div className="flex items-center gap-3">
        <StatusBadge status={plan.status} />
        <h1 className="text-lg font-bold">
          {conditions.occupation} への道標を作っています
        </h1>
      </div>
      <p className="text-sm text-stone-600">
        {semesterLabel(conditions.grade, conditions.term)}から 4 回生
        秋学期までを組みます。
      </p>
      {watch === "gave-up" ? (
        <div className="space-y-3 text-sm text-stone-700">
          <p>
            時間がかかっています。あとで
            <Link href="/plans" className="text-teal-800 underline">
              一覧
            </Link>
            から見てください。
          </p>
          <RetryButton onClick={retry} />
        </div>
      ) : (
        <p className="text-sm text-stone-500">
          ふだん 10〜30 秒かかります。このページを開いたままお待ちください。
        </p>
      )}
    </section>
  );
}

function Notice({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section
      role="alert"
      className="space-y-3 rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-900"
    >
      <h1 className="text-lg font-bold">{title}</h1>
      {children}
    </section>
  );
}

function RetryButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-md border border-stone-300 bg-white px-3 py-1.5 text-stone-800 hover:bg-stone-100"
    >
      もう一度確かめる
    </button>
  );
}
