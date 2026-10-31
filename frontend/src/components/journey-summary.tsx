import type { SemesterPlan, Term } from "@/lib/api/client";
import { RELEVANCE_LABELS, semesterLabel } from "@/lib/labels";
import { routeTotals } from "@/lib/roadmap";

export function JourneySummary({
  semesters,
  conditions,
  skills,
}: {
  semesters: SemesterPlan[];
  conditions: { grade: number; term: Term; credit_limit: number; year: number };
  skills: string[];
}) {
  const totals = routeTotals(semesters);
  const facts = [
    ["所要", `${semesters.length} 学期`],
    ["計", `${totals.credits} 単位`],
    [RELEVANCE_LABELS.core, `${totals.core} 科目`],
    [RELEVANCE_LABELS.foundation, `${totals.foundation} 科目`],
  ];
  return (
    <div className="max-w-2xl border-t-2 border-b border-t-ink border-b-line dark:border-t-ink/60">
      <div className="flex flex-wrap gap-x-4 border-b border-line py-2 text-sm">
        <span>
          <span className="font-bold">
            {semesterLabel(conditions.grade, conditions.term)}
          </span>{" "}
          発
        </span>
        {skills.length > 0 && (
          <div>
            経由{" "}
            <ul className="inline">
              {skills.map((skill, index) => (
                <li
                  key={`${index}-${skill}`}
                  className="inline after:content-['、'] last:after:content-none"
                >
                  {skill}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
      <dl className="grid grid-cols-2 gap-y-1 py-2.5 text-sm sm:flex sm:flex-wrap">
        {facts.map(([term, value]) => (
          <div
            key={term}
            className="flex items-baseline gap-1.5 sm:mr-5 sm:border-r sm:border-line sm:pr-5 sm:last:mr-0 sm:last:border-r-0 sm:last:pr-0"
          >
            <dt className="text-xs text-sub">{term}</dt>
            <dd className="font-bold tabular-nums">{value}</dd>
          </div>
        ))}
      </dl>
      <p className="border-t border-line py-1.5 text-label text-sub">
        1 学期 {conditions.credit_limit} 単位まで ・ {conditions.year}{" "}
        年度の時間割
      </p>
    </div>
  );
}
