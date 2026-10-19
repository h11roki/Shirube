import { CourseGrid } from "@/components/course-grid";
import { QueryLink } from "@/components/query-link";
import { WeekTable } from "@/components/week-table";
import type { SemesterPlan } from "@/lib/api/client";
import {
  CONTINUING_LABEL,
  EMPTY_SEMESTER_LABEL,
  semesterLabel,
  stationLabel,
} from "@/lib/labels";
import {
  pickSemester,
  semesterCourses,
  semesterKey,
  transfers,
} from "@/lib/roadmap";
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
  const all = semesterCourses(semester);
  const found = transfers(semesters);
  return (
    <div className="grid gap-4 motion-safe:animate-rise">
      <nav aria-label="学期" className="flex flex-wrap gap-1.5">
        {semesters.map((each, index) => {
          const current = each === semester;
          return (
            <QueryLink
              key={semesterKey(each)}
              href={resultViewHref(planPath, "timetable", semesterKey(each))}
              aria-current={current ? "page" : undefined}
              className={`rounded-full border-[1.5px] px-3.5 py-1 text-[13px] ${current ? "border-ink bg-note font-bold text-ink" : "border-line bg-sheet text-sub hover:text-ink"}`}
            >
              <span className="mr-1.5 text-[11px] text-route tabular-nums">
                {stationLabel(index)}
              </span>
              {semesterLabel(each.grade, each.term)} ・ {each.credits} 単位
            </QueryLink>
          );
        })}
      </nav>
      <div className="grid items-start gap-4 lg:grid-cols-[1.55fr_1fr]">
        <div className="min-w-0 rounded-lg border border-line bg-note p-3.5">
          <WeekTable courses={all} />
        </div>
        {all.length > 0 ? (
          <div className="grid min-w-0 gap-3">
            <CourseGrid courses={semester.courses} transfers={found} />
            {semester.continuing.length > 0 && (
              <p className="pt-1 text-xs font-bold text-sub">
                {CONTINUING_LABEL}(単位は春学期に数えます)
              </p>
            )}
            <CourseGrid courses={semester.continuing} transfers={found} />
          </div>
        ) : (
          <p className="text-sm text-sub">{EMPTY_SEMESTER_LABEL}</p>
        )}
      </div>
    </div>
  );
}
