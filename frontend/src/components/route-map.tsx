"use client";

import Link from "next/link";
import { type ReactNode, useId, useState } from "react";

import { CourseCard } from "@/components/course-card";
import { WeekTable } from "@/components/week-table";
import type { SemesterPlan } from "@/lib/api/client";
import { semesterLabel, slotsLabel } from "@/lib/labels";
import { semesterKey } from "@/lib/roadmap";
import { VIEWS_ANCHOR, resultViewHref } from "@/lib/result-view";

const STAGGER_MS = 120;

export function RouteMap({
  semesters,
  planPath,
  end,
}: {
  semesters: SemesterPlan[];
  planPath?: string;
  end: ReactNode;
}) {
  return (
    <ol className="relative grid gap-9 pl-12 before:absolute before:inset-y-2.5 before:left-4 before:w-1 before:rounded-full before:bg-route">
      {semesters.map((semester, index) => (
        <Station
          key={semesterKey(semester)}
          semester={semester}
          planPath={planPath}
          delayMs={index * STAGGER_MS}
        />
      ))}
      <li
        style={{ animationDelay: `${semesters.length * STAGGER_MS}ms` }}
        className="relative grid min-w-0 gap-1 before:absolute before:top-1.5 before:-left-[39px] before:size-[18px] before:rounded-full before:bg-pillar motion-safe:animate-rise"
      >
        {end}
      </li>
    </ol>
  );
}

function Station({
  semester,
  planPath,
  delayMs,
}: {
  semester: SemesterPlan;
  planPath?: string;
  delayMs: number;
}) {
  const [open, setOpen] = useState(false);
  const weekId = useId();
  const all = [...semester.courses, ...semester.continuing];
  return (
    <li
      style={{ animationDelay: `${delayMs}ms` }}
      className="relative grid min-w-0 gap-3 before:absolute before:top-1.5 before:-left-[39px] before:size-[18px] before:rounded-full before:border-4 before:border-route before:bg-paper motion-safe:animate-rise"
    >
      <h2 className="flex flex-wrap items-baseline gap-x-3.5 gap-y-1 font-serif text-xl font-bold">
        {semesterLabel(semester.grade, semester.term)}
        <span className="font-sans text-xs font-medium text-sub">
          {semester.credits} 単位 ・ {semester.courses.length} 科目
        </span>
      </h2>
      {semester.courses.length > 0 ? (
        <div className="grid gap-2.5 sm:grid-cols-[repeat(auto-fill,minmax(15rem,1fr))]">
          {semester.courses.map((course) => (
            <CourseCard key={course.section_code} course={course} />
          ))}
        </div>
      ) : (
        <p className="text-sm text-sub">この学期に置いた授業はありません。</p>
      )}
      {semester.continuing.length > 0 && (
        <p className="text-[13px] text-sub">
          春学期からの続き:{" "}
          {semester.continuing
            .map((course) => `${course.name}(${slotsLabel(course)})`)
            .join("、")}
        </p>
      )}
      {all.length > 0 && (
        <div className="flex flex-wrap gap-x-5 gap-y-2 text-sm">
          <button
            type="button"
            aria-expanded={open}
            aria-controls={weekId}
            onClick={() => setOpen(!open)}
            className="text-route underline underline-offset-4"
          >
            {open ? "この学期の時間割を閉じる ▴" : "この学期の時間割を開く ▾"}
          </button>
          {planPath && (
            <Link
              href={`${resultViewHref(planPath, "timetable", semesterKey(semester))}#${VIEWS_ANCHOR}`}
              className="text-route underline underline-offset-4"
            >
              時間割帳で見る →
            </Link>
          )}
        </div>
      )}
      <div
        id={weekId}
        hidden={!open}
        className="min-w-0 rounded-lg border border-line bg-note p-3.5 motion-safe:animate-rise"
      >
        <WeekTable courses={all} />
      </div>
    </li>
  );
}
