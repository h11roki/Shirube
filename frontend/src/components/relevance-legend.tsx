import { RELEVANCE_TONES } from "@/components/relevance-tones";
import type { Relevance } from "@/lib/api/client";
import { RELEVANCE_DESCRIPTIONS, RELEVANCE_LABELS } from "@/lib/labels";
import { RECOMMENDED_RELEVANCES } from "@/lib/roadmap";

export function RelevanceLegend({
  className = "",
  relevances = RECOMMENDED_RELEVANCES,
}: {
  className?: string;
  relevances?: Relevance[];
}) {
  return (
    <p
      className={`flex flex-wrap gap-x-4 gap-y-1 text-xs text-sub ${className}`}
    >
      {relevances.map((relevance) => (
        <span key={relevance} className="flex items-start gap-1.5">
          <span
            aria-hidden
            className={`mt-[0.2em] size-3 ${RELEVANCE_TONES[relevance].mark}`}
          />
          <span>
            <span className="font-bold text-ink">
              {RELEVANCE_LABELS[relevance]}
            </span>
            <span className="sr-only">、</span>
            <span className="ml-1">{RELEVANCE_DESCRIPTIONS[relevance]}</span>
          </span>
        </span>
      ))}
    </p>
  );
}
