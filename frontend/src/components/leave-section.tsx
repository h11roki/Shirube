"use client";

import { useRef, useState } from "react";

import { ConfirmButton } from "@/components/confirm-button";
import { OUTLINE_BUTTON } from "@/components/styles";
import {
  type TakenCourses,
  messageOf,
  requestJson,
  requestNothing,
} from "@/lib/api/client";
import {
  CONFIRM_LEAVE_LABEL,
  LEAVE_KEEPS,
  LEAVE_LABEL,
  LEFT_NOTICE,
  type TakenCount,
  leaveSummary,
} from "@/lib/labels";
import { signOutToTop } from "@/lib/sign-out";

export function LeaveSection({
  plans,
  onLeft,
}: {
  plans: number;
  onLeft: () => void;
}) {
  const [taken, setTaken] = useState<TakenCount>();
  const asked = useRef(0);

  function countTaken() {
    const ask = (asked.current += 1);
    setTaken(undefined);
    void requestJson<TakenCourses>("/api/taken-courses")
      .then(
        (answer): TakenCount => ({ count: answer.names.length }),
        (caught: unknown): TakenCount => ({ failure: messageOf(caught) }),
      )
      .then((counted) => {
        if (ask === asked.current) {
          setTaken(counted);
        }
      });
  }

  return (
    <section className="grid justify-items-start gap-3 border-t border-line pt-6">
      <h2 className="font-serif text-lg font-bold">退会する</h2>
      <ConfirmButton
        label={LEAVE_LABEL}
        note={`${leaveSummary(plans, taken)}${LEAVE_KEEPS}`}
        confirmLabel={CONFIRM_LEAVE_LABEL}
        onOpen={countTaken}
        onConfirm={async () => {
          await requestNothing("/api/me", { method: "DELETE" });
          onLeft();
          await signOutToTop();
        }}
      />
    </section>
  );
}

export function LeftNotice() {
  return (
    <form action={signOutToTop} className="grid justify-items-start gap-3">
      <p role="status" className="text-sm">
        {LEFT_NOTICE}
      </p>
      <button type="submit" className={OUTLINE_BUTTON}>
        ログアウト
      </button>
    </form>
  );
}
