import { RELEVANCES, RELEVANCE_TONES } from "@/components/relevance-tones";
import { RELEVANCE_DESCRIPTIONS, RELEVANCE_LABELS } from "@/lib/labels";

export function RelevanceLegend({ className = "" }: { className?: string }) {
  return (
    <p
      className={`flex flex-wrap gap-x-4 gap-y-1 text-xs text-sub ${className}`}
    >
      {RELEVANCES.map((relevance) => (
        <span key={relevance} className="flex items-start gap-1.5">
          <span
            aria-hidden
            className={`mt-[0.2em] size-3 ${RELEVANCE_TONES[relevance].mark}`}
          />
          <span>
            <span className="font-bold text-ink">
              {RELEVANCE_LABELS[relevance]}
            </span>
            <span className="sr-only">、</span>{" "}
            {RELEVANCE_DESCRIPTIONS[relevance]}
          </span>
        </span>
      ))}
    </p>
  );
}
