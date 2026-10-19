import type { SemesterPlan, Term } from "@/lib/api/client";
import {
  RELEVANCE_LABELS,
  goalStationLabel,
  semesterLabel,
} from "@/lib/labels";
import { routeTotals } from "@/lib/roadmap";

export function JourneySummary({
  semesters,
  conditions,
}: {
  semesters: SemesterPlan[];
  conditions: { grade: number; term: Term };
}) {
  const totals = routeTotals(semesters);
  const facts = [
    ["所要", `${semesters.length} 学期`],
    ["計", `${totals.credits} 単位`],
    [RELEVANCE_LABELS.core, `${totals.core} 科目`],
    [RELEVANCE_LABELS.foundation, `${totals.foundation} 科目`],
  ];
  return (
    <div className="max-w-xl overflow-hidden rounded-lg border border-line bg-sheet shadow-paper">
      <p className="flex flex-wrap items-center gap-x-2.5 gap-y-1 bg-route px-4 py-2 text-sm font-bold text-paper">
        <span className="rounded-xs border border-paper/60 px-1 text-[11px]">
          出発
        </span>
        {semesterLabel(conditions.grade, conditions.term)}
        <span aria-hidden>→</span>
        <span className="rounded-xs border border-paper/60 px-1 text-[11px]">
          到着
        </span>
        卒業
        <span className="text-[11px] tabular-nums">
          {goalStationLabel(semesters.length)}
        </span>
      </p>
      <dl className="flex flex-wrap gap-x-6 gap-y-1 px-4 py-2.5 text-sm">
        {facts.map(([term, value]) => (
          <div key={term} className="flex items-baseline gap-1.5">
            <dt className="text-xs text-sub">{term}</dt>
            <dd className="font-bold tabular-nums">{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
