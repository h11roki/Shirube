"use client";

import { OUTLINE_BUTTON } from "@/components/styles";
import type { Failure } from "@/lib/api/client";
import { RETRY_LABEL, SIGN_IN_AGAIN_LABEL } from "@/lib/labels";

export function SignInAgainButton() {
  return (
    <button
      type="button"
      onClick={() => window.location.reload()}
      className={OUTLINE_BUTTON}
    >
      {SIGN_IN_AGAIN_LABEL}
    </button>
  );
}

export function FailureNotice({
  lead,
  failure,
  onRetry,
  className,
}: {
  lead?: string;
  failure: Failure;
  onRetry?: () => void;
  className?: string;
}) {
  return (
    <div
      role="alert"
      className={`flex flex-wrap items-center gap-3 text-sm${className ? ` ${className}` : ""}`}
    >
      <p className="text-danger">
        {lead}
        {failure.message}
      </p>
      {failure.signedOut ? (
        <SignInAgainButton />
      ) : (
        onRetry && (
          <button type="button" onClick={onRetry} className={OUTLINE_BUTTON}>
            {RETRY_LABEL}
          </button>
        )
      )}
    </div>
  );
}
