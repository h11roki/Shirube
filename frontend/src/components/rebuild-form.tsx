"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  type FormEvent,
  useEffect,
  useRef,
  useState,
  useTransition,
} from "react";

import { FailureNotice } from "@/components/failure-notice";
import {
  FIELD,
  OUTLINE_BUTTON,
  PRIMARY_BUTTON,
  SMALL_BUTTON,
  STANDALONE_LINK,
} from "@/components/styles";
import {
  ApiError,
  type Plan,
  UNPROCESSABLE,
  createPlan,
  messageOf,
} from "@/lib/api/client";
import {
  CANCEL_LABEL,
  OCCUPATION_LABEL,
  REBUILD_LABEL,
  REBUILD_NOTE,
  REBUILD_ON_FORM_LABEL,
  REBUILD_SUBMIT_LABEL,
} from "@/lib/labels";
import {
  MAX_OCCUPATION_LENGTH,
  rebuildProblem,
  rebuildRequest,
} from "@/lib/plan-request";

export function RebuildForm({
  conditions,
}: {
  conditions: Plan["conditions"];
}) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [occupation, setOccupation] = useState("");
  const [problem, setProblem] = useState<string>();
  const [conditionsRefused, setConditionsRefused] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [navigating, startNavigation] = useTransition();
  const busy = submitting || navigating;
  const opener = useRef<HTMLButtonElement>(null);
  const field = useRef<HTMLInputElement>(null);
  const opened = useRef(false);

  useEffect(() => {
    if (open) {
      opened.current = true;
      field.current?.focus();
    } else if (opened.current) {
      opener.current?.focus();
    }
  }, [open]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) {
      return;
    }
    const refused = rebuildProblem(occupation, conditions);
    if (refused) {
      setProblem(refused);
      field.current?.focus();
      return;
    }
    setSubmitting(true);
    setProblem(undefined);
    setConditionsRefused(false);
    try {
      const plan = await createPlan(rebuildRequest(occupation, conditions));
      startNavigation(() => router.push(`/plans/${plan.id}`));
    } catch (error) {
      setProblem(messageOf(error));
      setConditionsRefused(
        error instanceof ApiError && error.status === UNPROCESSABLE,
      );
      setSubmitting(false);
    }
  }

  if (!open) {
    return (
      <button
        ref={opener}
        type="button"
        onClick={() => {
          setOccupation("");
          setProblem(undefined);
          setConditionsRefused(false);
          setOpen(true);
        }}
        className={SMALL_BUTTON}
      >
        {REBUILD_LABEL}
      </button>
    );
  }
  return (
    <form
      onSubmit={submit}
      aria-label={REBUILD_LABEL}
      className="grid w-full max-w-md gap-2 border border-line bg-sheet p-3 text-sm"
    >
      <label htmlFor="rebuild-occupation" className="font-medium">
        {OCCUPATION_LABEL}
      </label>
      <p id="rebuild-note" className="text-sub">
        {REBUILD_NOTE}
      </p>
      <input
        ref={field}
        id="rebuild-occupation"
        className={FIELD}
        value={occupation}
        onChange={(event) => setOccupation(event.target.value)}
        maxLength={MAX_OCCUPATION_LENGTH}
        aria-describedby="rebuild-note"
      />
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          aria-disabled={busy}
          onClick={() => {
            if (!busy) {
              setOpen(false);
            }
          }}
          className={`${OUTLINE_BUTTON} aria-disabled:opacity-50`}
        >
          {CANCEL_LABEL}
        </button>
        <button
          type="submit"
          aria-disabled={busy}
          className={`px-4 py-1.5 font-medium aria-disabled:opacity-50 ${PRIMARY_BUTTON}`}
        >
          {REBUILD_SUBMIT_LABEL}
        </button>
      </div>
      {problem && <FailureNotice message={problem} />}
      {conditionsRefused && (
        <Link href="/" className={`justify-self-start ${STANDALONE_LINK}`}>
          {REBUILD_ON_FORM_LABEL}
        </Link>
      )}
    </form>
  );
}
