"use client";

import { OUTLINE_BUTTON } from "@/components/styles";
import { RETRY_LABEL } from "@/lib/labels";

export function FailureNotice({
  lead,
  message,
  onRetry,
  className,
}: {
  lead?: string;
  message: string;
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
        {message}
      </p>
      {onRetry && (
        <button type="button" onClick={onRetry} className={OUTLINE_BUTTON}>
          {RETRY_LABEL}
        </button>
      )}
    </div>
  );
}
