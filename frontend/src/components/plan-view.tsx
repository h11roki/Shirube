"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";

import { PlanResultView } from "@/components/plan-result";
import { ProgressSteps } from "@/components/progress-steps";
import {
  ApiError,
  type Plan,
  UNAUTHORIZED,
  isTemporary,
  messageOf,
  requestJson,
} from "@/lib/api/client";
import { semesterLabel } from "@/lib/labels";
import {
  POLL_INTERVAL_MS,
  POLL_REQUEST_TIMEOUT_MS,
  type Watch,
  watchAfterFailure,
  watchState,
} from "@/lib/polling";

const BUTTON_CLASS =
  "rounded-full border border-line bg-sheet px-4 py-1.5 text-ink hover:border-ink";

export function PlanView() {
  const { id } = useParams<{ id: string }>();
  const [plan, setPlan] = useState<Plan>();
  const [watch, setWatch] = useState<Watch>("waiting");
  const [error, setError] = useState<{ message: string; status: number }>();
  const [round, setRound] = useState(0);

  useEffect(() => {
    let active = true;
    let seen = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const leaving = new AbortController();
    const startedAt = Date.now();
    async function poll() {
      try {
        const latest = await requestJson<Plan>(
          `/api/plans/${encodeURIComponent(id)}`,
          {
            signal: AbortSignal.any([
              leaving.signal,
              AbortSignal.timeout(POLL_REQUEST_TIMEOUT_MS),
            ]),
          },
        );
        if (!active) {
          return;
        }
        const state = watchState(latest.status, Date.now() - startedAt);
        seen = true;
        setPlan(latest);
        setWatch(state);
        setError(undefined);
        if (state === "waiting") {
          timer = setTimeout(poll, POLL_INTERVAL_MS);
        }
      } catch (caught) {
        if (!active) {
          return;
        }
        const next = watchAfterFailure(
          isTemporary(caught),
          Date.now() - startedAt,
        );
        if (next === "waiting") {
          timer = setTimeout(poll, POLL_INTERVAL_MS);
        } else if (next === "gave-up" && seen) {
          setWatch(next);
        } else {
          setError({
            message: messageOf(caught),
            status: caught instanceof ApiError ? caught.status : 0,
          });
        }
      }
    }
    void poll();
    return () => {
      active = false;
      clearTimeout(timer);
      leaving.abort();
    };
  }, [id, round]);

  function retry() {
    setError(undefined);
    setWatch("waiting");
    setRound((current) => current + 1);
  }

  if (error?.status === UNAUTHORIZED) {
    return (
      <Notice title="ログインが切れました">
        <button
          type="button"
          onClick={() => window.location.reload()}
          className={BUTTON_CLASS}
        >
          ログインし直す
        </button>
      </Notice>
    );
  }
  if (error) {
    return (
      <Notice title="道標を読み込めませんでした">
        <p>{error.message}</p>
        <RetryButton onClick={retry} />
      </Notice>
    );
  }
  if (!plan) {
    return <p className="text-sm text-sub">読み込んでいます</p>;
  }
  if (plan.status === "succeeded") {
    return plan.result ? (
      <PlanResultView plan={plan} result={plan.result} />
    ) : (
      <Notice title="道標の中身を読めませんでした">
        <RetryButton onClick={retry} />
      </Notice>
    );
  }
  if (plan.status === "failed") {
    return (
      <Notice title="道標を作れませんでした">
        <p>{plan.failure}</p>
        <Link href="/" className="text-route underline underline-offset-4">
          もう一度作る
        </Link>
      </Notice>
    );
  }
  const { conditions } = plan;
  return (
    <section
      aria-live="polite"
      className="mx-auto grid max-w-xl gap-6 rounded-lg border border-line bg-sheet p-6 shadow-paper motion-safe:animate-rise sm:p-8"
    >
      <div className="grid gap-1.5">
        <p className="text-xs font-bold tracking-[0.28em] text-pillar">
          目的地 ── {conditions.occupation}
        </p>
        <h1 className="font-serif text-2xl font-extrabold text-balance">
          {conditions.occupation}への道標を作っています
        </h1>
        <p className="text-sm text-sub">
          {semesterLabel(conditions.grade, conditions.term)}
          から卒業までを組みます。
        </p>
      </div>
      <ProgressSteps status={plan.status} stage={plan.stage} />
      {watch === "gave-up" ? (
        <div className="grid justify-items-start gap-3 text-sm">
          <p>
            時間がかかっています。あとで
            <Link
              href="/plans"
              className="text-route underline underline-offset-4"
            >
              一覧
            </Link>
            から見てください。
          </p>
          <RetryButton onClick={retry} />
        </div>
      ) : (
        <p className="text-xs text-sub">
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
      className="mx-auto grid max-w-xl justify-items-start gap-3 rounded-lg border border-danger/30 bg-danger-soft p-6 text-sm"
    >
      <h1 className="font-serif text-xl font-bold text-danger">{title}</h1>
      {children}
    </section>
  );
}

function RetryButton({ onClick }: { onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} className={BUTTON_CLASS}>
      もう一度確かめる
    </button>
  );
}
