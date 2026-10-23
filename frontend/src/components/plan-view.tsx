"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { type ReactNode, useEffect, useRef, useState } from "react";

import { ConfirmButton } from "@/components/confirm-button";
import { Notice } from "@/components/notice";
import { PlanProgress } from "@/components/plan-progress";
import { PlanResultView } from "@/components/plan-result";
import {
  OUTLINE_BUTTON,
  STANDALONE_LINK,
  TEXT_LINK,
} from "@/components/styles";
import {
  ApiError,
  type Plan,
  NOT_FOUND,
  deletePlan,
  isTemporary,
  messageOf,
  requestJson,
} from "@/lib/api/client";
import {
  CONFIRM_DELETE_LABEL,
  DELETE_PLAN_LABEL,
  DELETE_PLAN_NOTE,
  completionNotice,
  planTitlePrefix,
} from "@/lib/labels";
import {
  POLL_INTERVAL_MS,
  POLL_REQUEST_TIMEOUT_MS,
  type Watch,
  watchAfterFailure,
  watchState,
} from "@/lib/polling";

const ANNOUNCE_DELAY_MS = 500;

export function PlanView() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [plan, setPlan] = useState<Plan>();
  const [watch, setWatch] = useState<Watch>("waiting");
  const [error, setError] = useState<{ message: string; status: number }>();
  const [round, setRound] = useState(0);
  const [progressSeenFor, setProgressSeenFor] = useState<string>();
  const [notice, setNotice] = useState("");
  const deleted = useRef(false);
  const sawProgress = progressSeenFor === id;
  const completion = plan ? completionNotice(plan, sawProgress) : "";
  const prefix =
    plan && !error ? planTitlePrefix(plan, sawProgress) : undefined;

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
        if (!active || deleted.current) {
          return;
        }
        const state = watchState(latest.status, Date.now() - startedAt);
        seen = true;
        setPlan(latest);
        if (state !== "finished") {
          setProgressSeenFor(id);
        }
        setWatch(state);
        setError(undefined);
        if (state === "waiting") {
          timer = setTimeout(poll, POLL_INTERVAL_MS);
        }
      } catch (caught) {
        if (!active || deleted.current) {
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

  useEffect(() => {
    if (prefix === undefined) {
      return;
    }
    const base = document.title;
    const title = `${prefix}${base}`;
    document.title = title;
    return () => {
      if (document.title === title) {
        document.title = base;
      }
    };
  }, [prefix]);

  useEffect(() => {
    const timer = setTimeout(() => setNotice(completion), ANNOUNCE_DELAY_MS);
    return () => clearTimeout(timer);
  }, [completion]);

  function retry() {
    setError(undefined);
    setWatch("waiting");
    setRound((current) => current + 1);
  }

  if (error?.status === NOT_FOUND) {
    return (
      <Notice title="道標が見つかりません">
        <p>消した道標か、URL が違うかもしれません。</p>
        <Link href="/plans" className={STANDALONE_LINK}>
          自分の道標へ
        </Link>
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
  let body: ReactNode;
  if (plan.status === "succeeded") {
    body = plan.result ? (
      <PlanResultView plan={plan} result={plan.result} onAnswered={setPlan} />
    ) : (
      <Notice title="道標の中身を読めませんでした">
        <RetryButton onClick={retry} />
      </Notice>
    );
  } else if (plan.status === "failed") {
    body = (
      <Notice title="道標を作れませんでした">
        <p>{plan.failure}</p>
        <Link href="/" className={STANDALONE_LINK}>
          もう一度作る
        </Link>
      </Notice>
    );
  } else {
    body = (
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
    );
  }
  return (
    <div className="grid gap-6">
      <p role="status" className="sr-only">
        {notice}
      </p>
      {body}
      <div
        className={
          plan.status === "succeeded" ? undefined : "mx-auto w-full max-w-xl"
        }
      >
        <ConfirmButton
          label={DELETE_PLAN_LABEL}
          note={DELETE_PLAN_NOTE}
          confirmLabel={CONFIRM_DELETE_LABEL}
          onConfirm={async () => {
            await deletePlan(plan.id);
            deleted.current = true;
            router.replace("/plans");
          }}
        />
      </div>
    </div>
  );
}

function RetryButton({ onClick }: { onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} className={OUTLINE_BUTTON}>
      もう一度確かめる
    </button>
  );
}
