"use client";

import { useState } from "react";

import { ConfirmButton } from "@/components/confirm-button";
import { OUTLINE_BUTTON } from "@/components/styles";
import {
  type TakenCourses,
  requestJson,
  requestNothing,
} from "@/lib/api/client";
import {
  CONFIRM_LEAVE_LABEL,
  LEAVE_KEEPS,
  LEAVE_LABEL,
  LEFT_NOTICE,
  leaveSummary,
} from "@/lib/labels";
import { signOutToTop } from "@/lib/sign-out";

export function LeaveSection({ plans }: { plans: number }) {
  const [taken, setTaken] = useState<number>();
  const [left, setLeft] = useState(false);

  function countTaken() {
    setTaken(undefined);
    requestJson<TakenCourses>("/api/taken-courses").then(
      (answer) => setTaken(answer.names.length),
      () => setTaken(undefined),
    );
  }

  return (
    <section className="grid justify-items-start gap-3 border-t border-line pt-6">
      <h2 className="font-serif text-lg font-bold">退会する</h2>
      {left ? (
        <form action={signOutToTop} className="grid justify-items-start gap-3">
          <p role="status" className="text-sm">
            {LEFT_NOTICE}
          </p>
          <button type="submit" className={OUTLINE_BUTTON}>
            ログアウト
          </button>
        </form>
      ) : (
        <ConfirmButton
          label={LEAVE_LABEL}
          note={`${leaveSummary(plans, taken)}${LEAVE_KEEPS}`}
          confirmLabel={CONFIRM_LEAVE_LABEL}
          onOpen={countTaken}
          onConfirm={async () => {
            await requestNothing("/api/me", { method: "DELETE" });
            setLeft(true);
            await signOutToTop();
          }}
        />
      )}
    </section>
  );
}
