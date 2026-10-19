"use client";

import { useEffect, useRef, useState } from "react";

import { type TakenCourses, messageOf, requestJson } from "@/lib/api/client";
import { forgetTakenLabel } from "@/lib/labels";

export function TakenCourseList() {
  const [names, setNames] = useState<string[]>();
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string>();
  const [forgotten, setForgotten] = useState(false);
  const summary = useRef<HTMLElement>(null);

  useEffect(() => {
    let active = true;
    requestJson<TakenCourses>("/api/taken-courses")
      .then((answer) => {
        if (active) {
          setNames(answer.names);
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setFailure(messageOf(error));
        }
      });
    return () => {
      active = false;
    };
  }, []);

  async function forget(name: string) {
    setBusy(true);
    setFailure(undefined);
    try {
      const answer = await requestJson<TakenCourses>(
        `/api/taken-courses/${encodeURIComponent(name)}`,
        { method: "DELETE" },
      );
      setNames(answer.names);
      setForgotten(true);
    } catch (error) {
      setFailure(messageOf(error));
    } finally {
      setBusy(false);
      summary.current?.focus();
    }
  }

  if (!names) {
    return failure ? (
      <p role="alert" className="text-sm text-danger">
        もう取ったと答えた授業を読み込めませんでした: {failure}
      </p>
    ) : null;
  }
  if (names.length === 0 && !forgotten && !failure) {
    return null;
  }
  return (
    <details className="rounded-lg border border-line bg-paper p-4">
      <summary ref={summary} className="cursor-pointer text-sm font-medium">
        もう取ったと答えた授業({names.length} 科目)
      </summary>
      <p className="mt-3 text-sm text-sub">
        道標を作るとき、これらの授業は推薦の候補から除きます。まだ取っていない授業は取り消してください。
      </p>
      {names.length === 0 && (
        <p className="mt-3 text-sm text-sub">
          もう取ったと答えた授業はありません。取り消した授業は、次に作る道標から候補に戻ります。
        </p>
      )}
      {failure && (
        <p role="alert" className="mt-3 text-sm text-danger">
          {failure}
        </p>
      )}
      <ul className="mt-3 grid gap-2 text-sm">
        {names.map((name) => (
          <li
            key={name}
            className="flex flex-wrap items-center gap-x-3 gap-y-1"
          >
            <span className="font-bold">{name}</span>
            <button
              type="button"
              disabled={busy}
              onClick={() => void forget(name)}
              aria-label={forgetTakenLabel(name)}
              className="rounded-full border border-line px-3 py-0.5 text-xs text-sub hover:border-ink hover:text-ink disabled:opacity-50"
            >
              取り消す
            </button>
          </li>
        ))}
      </ul>
    </details>
  );
}
