"use client";

import { type RefObject, useCallback, useEffect, useMemo, useRef } from "react";

import { CourseGrid } from "@/components/course-grid";
import { QueryLink, pushQuery } from "@/components/query-link";
import {
  TransferFocusContext,
  useTransferFocusValue,
} from "@/components/transfer-focus";
import { WeekTable } from "@/components/week-table";
import type { SemesterPlan } from "@/lib/api/client";
import {
  CONTINUING_LABEL,
  EMPTY_SEMESTER_LABEL,
  semesterLabel,
  stationLabel,
} from "@/lib/labels";
import {
  type Transfer,
  pickSemester,
  semesterCourses,
  semesterKey,
  transfers,
} from "@/lib/roadmap";
import { resultViewHref } from "@/lib/result-view";

function reachableEverywhere(): boolean {
  return true;
}

function revealPending(pending: RefObject<string | null>) {
  const section = pending.current;
  pending.current = null;
  if (section) {
    document
      .getElementById(`ticket-${section}`)
      ?.scrollIntoView({ block: "center" });
  }
}

export function TimetableBook({
  semesters,
  selected,
  planPath,
}: {
  semesters: SemesterPlan[];
  selected: string | null;
  planPath: string;
}) {
  const found = useMemo(() => transfers(semesters), [semesters]);
  const pending = useRef<string | null>(null);
  const go = useCallback(
    (transfer: Transfer) => {
      pending.current = transfer.pillarSection;
      const moved = pushQuery(
        resultViewHref(planPath, "timetable", semesterKey(transfer.semester)),
      );
      if (!moved) {
        revealPending(pending);
      }
    },
    [planPath],
  );
  const focusing = useTransferFocusValue(found, reachableEverywhere, go);
  const semester = pickSemester(semesters, selected);
  const shownKey = semester ? semesterKey(semester) : null;
  useEffect(() => revealPending(pending), [shownKey]);
  if (!semester) {
    return <p className="text-sm text-sub">学期がありません。</p>;
  }
  const all = semesterCourses(semester);
  return (
    <TransferFocusContext.Provider value={focusing}>
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
              {semester.courses.length > 0 && (
                <CourseGrid courses={semester.courses} transfers={found} />
              )}
              {semester.continuing.length > 0 && (
                <p className="pt-1 text-xs font-bold text-sub">
                  {CONTINUING_LABEL}(単位は春学期に数えます)
                </p>
              )}
              {semester.continuing.length > 0 && (
                <CourseGrid courses={semester.continuing} transfers={found} />
              )}
            </div>
          ) : (
            <p className="text-sm text-sub">{EMPTY_SEMESTER_LABEL}</p>
          )}
        </div>
      </div>
    </TransferFocusContext.Provider>
  );
}
