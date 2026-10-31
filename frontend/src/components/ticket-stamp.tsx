import { RELEVANCE_TONES } from "@/components/relevance-tones";
import type { Relevance } from "@/lib/api/client";
import { RELEVANCE_LABELS } from "@/lib/labels";
import { stampTilt } from "@/lib/ticket-face";

export function TicketStamp({
  course,
  className,
  delayMs,
}: {
  course: { name: string; relevance: Relevance };
  className: string;
  delayMs?: number;
}) {
  return (
    <span
      aria-hidden
      style={{
        rotate: `${stampTilt(course.name)}deg`,
        animationDelay: delayMs === undefined ? undefined : `${delayMs}ms`,
      }}
      className={`${className} ${RELEVANCE_TONES[course.relevance].stamp}`}
    >
      {RELEVANCE_LABELS[course.relevance]}
    </span>
  );
}
