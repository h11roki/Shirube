"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";

import { DeletePlanButton } from "@/components/delete-plan-button";
import { PlanProgress } from "@/components/plan-progress";
import { PlanResultView } from "@/components/plan-result";
import { OUTLINE_BUTTON, TEXT_LINK } from "@/components/styles";
import {
  ApiError,
  type Plan,
  UNAUTHORIZED,
  isTemporary,
  messageOf,
  requestJson,
} from "@/lib/api/client";
import {
  POLL_INTERVAL_MS,
  POLL_REQUEST_TIMEOUT_MS,
  type Watch,
  watchAfterFailure,
  watchState,
} from "@/lib/polling";

export function PlanView() {
  const { id } = useParams<{ id: string }>();
  const [plan, setPlan] = useState<Plan>();
  const [watch, setWatch] = useState<Watch>("waiting");
  const [error, setError] = useState<{ message: string; status: number }>();
  const [round, setRound] = useState(0);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (deleting) {
      return;
    }
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
  }, [id, round, deleting]);

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
          className={OUTLINE_BUTTON}
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
      <PlanResultView plan={plan} result={plan.result} onAnswered={setPlan} />
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
        <Link href="/" className={TEXT_LINK}>
          もう一度作る
        </Link>
        <DeletePlanButton id={plan.id} />
      </Notice>
    );
  }
  return (
    <div className="grid gap-6">
      <PlanProgress
        plan={plan}
        stalled={
          watch === "gave-up" ? (
            <div className="grid justify-items-start gap-3 text-sm">
              <p>
                時間がかかっています。あとで
                <Link href="/plans" className={TEXT_LINK}>
                  一覧
                </Link>
                から見てください。
              </p>
              <RetryButton onClick={retry} />
            </div>
          ) : undefined
        }
      />
      <div className="mx-auto w-full max-w-xl">
        <DeletePlanButton id={plan.id} onDeleting={setDeleting} />
      </div>
    </div>
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
    <button type="button" onClick={onClick} className={OUTLINE_BUTTON}>
      もう一度確かめる
    </button>
  );
}
