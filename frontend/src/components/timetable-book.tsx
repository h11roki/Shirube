import Link from "next/link";

import { WeekTable } from "@/components/week-table";
import type { SemesterPlan } from "@/lib/api/client";
import { placementLabel, roleLabel, semesterLabel } from "@/lib/labels";
import { pickSemester, semesterKey } from "@/lib/roadmap";
import { resultViewHref } from "@/lib/result-view";

export function TimetableBook({
  semesters,
  selected,
  planPath,
}: {
  semesters: SemesterPlan[];
  selected: string | null;
  planPath: string;
}) {
  const semester = pickSemester(semesters, selected);
  if (!semester) {
    return <p className="text-sm text-sub">学期がありません。</p>;
  }
  const notes = [
    ...semester.courses.map((course) => ({ course, continuing: false })),
    ...semester.continuing.map((course) => ({ course, continuing: true })),
  ];
  return (
    <div className="grid gap-4 motion-safe:animate-rise">
      <nav aria-label="学期" className="flex flex-wrap gap-1.5">
        {semesters.map((each) => {
          const current = each === semester;
          return (
            <Link
              key={semesterKey(each)}
              href={resultViewHref(planPath, "timetable", semesterKey(each))}
              scroll={false}
              aria-current={current ? "page" : undefined}
              className={`rounded-full border-[1.5px] px-3.5 py-1 text-[13px] ${current ? "border-ink bg-note font-bold text-ink" : "border-line bg-sheet text-sub hover:text-ink"}`}
            >
              {semesterLabel(each.grade, each.term)} ・ {each.credits} 単位
            </Link>
          );
        })}
      </nav>
      <div className="grid items-start gap-4 lg:grid-cols-[1.55fr_1fr]">
        <div className="min-w-0 rounded-lg border border-line bg-note p-3.5">
          <WeekTable courses={notes.map((note) => note.course)} />
        </div>
        {notes.length > 0 ? (
          <ul className="grid min-w-0 gap-2.5">
            {notes.map(({ course, continuing }) => (
              <li
                key={course.section_code}
                className="grid gap-1 rounded-lg border border-line bg-note px-3.5 py-3"
              >
                <p className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                  <span
                    className={`rounded-sm px-1.5 text-[11px] font-bold text-paper ${course.relevance === "core" ? "bg-pillar" : "bg-route"}`}
                  >
                    {roleLabel(course)}
                  </span>
                  <span className="font-bold">{course.name}</span>
                </p>
                <p className="text-[13px] leading-relaxed text-sub">
                  {course.reason}
                </p>
                <p className="text-xs text-sub tabular-nums">
                  {continuing ? "春学期からの続き" : placementLabel(course)}
                  {!course.class_confirmed && (
                    <span className="text-pillar"> ・ クラス未確定</span>
                  )}
                </p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-sub">この学期に置いた授業はありません。</p>
        )}
      </div>
    </div>
  );
}
