"use client";

import { useEffect, useState } from "react";

import { ConfirmButton } from "@/components/confirm-button";
import {
  type TakenCourses,
  requestJson,
  requestNothing,
} from "@/lib/api/client";
import {
  CONFIRM_LEAVE_LABEL,
  LEAVE_KEEPS,
  LEAVE_LABEL,
  LISTED_PLANS,
  leaveSummary,
} from "@/lib/labels";
import { signOutToTop } from "@/lib/sign-out";

export function LeaveSection({ plans }: { plans: number }) {
  const [taken, setTaken] = useState<number>();

  useEffect(() => {
    let active = true;
    requestJson<TakenCourses>("/api/taken-courses")
      .then((answer) => {
        if (active) {
          setTaken(answer.names.length);
        }
      })
      .catch(() => {
        if (active) {
          setTaken(undefined);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <section className="grid justify-items-start gap-3 border-t border-line pt-6">
      <h2 className="font-serif text-lg font-bold">退会する</h2>
      <ConfirmButton
        label={LEAVE_LABEL}
        note={`${leaveSummary(plans, LISTED_PLANS, taken)}${LEAVE_KEEPS}`}
        confirmLabel={CONFIRM_LEAVE_LABEL}
        onConfirm={async () => {
          await requestNothing("/api/me", { method: "DELETE" });
          await signOutToTop();
        }}
      />
    </section>
  );
}
