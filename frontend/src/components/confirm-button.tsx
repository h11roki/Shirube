"use client";

import { useEffect, useRef, useState } from "react";

import { FailureNotice } from "@/components/failure-notice";
import { OUTLINE_BUTTON } from "@/components/styles";
import { messageOf } from "@/lib/api/client";
import { CANCEL_LABEL } from "@/lib/labels";

export function ConfirmButton({
  label,
  name,
  note,
  confirmLabel,
  onOpen,
  onConfirm,
}: {
  label: string;
  name?: string;
  note: string;
  confirmLabel: string;
  onOpen?: () => void;
  onConfirm: () => Promise<void>;
}) {
  const [asking, setAsking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string>();
  const start = useRef<HTMLButtonElement>(null);
  const cancel = useRef<HTMLButtonElement>(null);
  const opened = useRef(false);

  useEffect(() => {
    if (asking) {
      opened.current = true;
      cancel.current?.focus();
    } else if (opened.current) {
      start.current?.focus();
    }
  }, [asking]);

  async function confirm() {
    if (busy) {
      return;
    }
    setBusy(true);
    setFailure(undefined);
    try {
      await onConfirm();
    } catch (error) {
      setFailure(messageOf(error));
      setBusy(false);
    }
  }

  if (!asking) {
    return (
      <button
        ref={start}
        type="button"
        aria-label={name}
        onClick={() => {
          setFailure(undefined);
          setAsking(true);
          onOpen?.();
        }}
        className="rounded-xs border border-edge px-3 py-1 text-sm text-sub hover:border-danger hover:text-danger"
      >
        {label}
      </button>
    );
  }
  return (
    <div
      role="group"
      aria-label={name ?? label}
      className="grid max-w-md basis-full gap-2 border border-danger/30 bg-danger-soft p-3 text-sm"
    >
      <p className="text-ink">{note}</p>
      <div className="flex flex-wrap gap-2">
        <button
          ref={cancel}
          type="button"
          aria-disabled={busy}
          onClick={() => {
            if (!busy) {
              setAsking(false);
            }
          }}
          className={`${OUTLINE_BUTTON} aria-disabled:opacity-50`}
        >
          {CANCEL_LABEL}
        </button>
        <button
          type="button"
          aria-disabled={busy}
          onClick={() => void confirm()}
          className="rounded-xs bg-danger px-4 py-1.5 font-medium text-paper hover:opacity-90 aria-disabled:opacity-50"
        >
          {confirmLabel}
        </button>
      </div>
      {failure && <FailureNotice message={failure} />}
    </div>
  );
}
