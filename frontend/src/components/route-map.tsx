"use client";

import { type CSSProperties, type ReactNode, useId, useState } from "react";

import { CourseGrid } from "@/components/course-grid";
import { QueryLink } from "@/components/query-link";
import { StationBoard } from "@/components/station-board";
import { TEXT_LINK } from "@/components/styles";
import { WeekTable } from "@/components/week-table";
import type { SemesterPlan } from "@/lib/api/client";
import {
  CONTINUING_LABEL,
  EMPTY_SEMESTER_LABEL,
  slotsLabel,
} from "@/lib/labels";
import { STAGGER_MS } from "@/lib/motion";
import {
  type Transfer,
  semesterCourses,
  semesterKey,
  transfers,
} from "@/lib/roadmap";
import { VIEWS_ANCHOR, resultViewHref } from "@/lib/result-view";

const GOAL_PRESS_MS = 300;
const LINE_DELAY_MS = 250;

export function RouteMap({
  semesters,
  shown = semesters.length,
  planPath,
  end,
}: {
  semesters: SemesterPlan[];
  shown?: number;
  planPath?: string;
  end: ReactNode;
}) {
  const found = transfers(semesters);
  const visible = semesters.slice(0, shown);
  const arrive = visible.length * STAGGER_MS;
  return (
    <ol className="relative grid gap-9 pl-12">
      {visible.map((semester, index) => (
        <Station
          key={semesterKey(semester)}
          index={index}
          semesters={semesters}
          transfers={found}
          planPath={planPath}
          delayMs={index * STAGGER_MS}
        />
      ))}
      <li
        style={
          {
            animationDelay: `${arrive}ms`,
            "--arrive": `${arrive + GOAL_PRESS_MS}ms`,
          } as CSSProperties
        }
        className="relative min-w-0 before:absolute before:top-9 before:-left-[42px] before:z-[1] before:size-6 before:rounded-full before:bg-pillar before:shadow-[0_0_0_4px_var(--paper)] after:absolute after:top-0 after:-left-[32px] after:h-12 after:w-1 after:bg-route motion-safe:animate-rise"
      >
        {end}
      </li>
    </ol>
  );
}

function Station({
  index,
  semesters,
  transfers,
  planPath,
  delayMs,
}: {
  index: number;
  semesters: SemesterPlan[];
  transfers: Map<string, Transfer>;
  planPath?: string;
  delayMs: number;
}) {
  const [open, setOpen] = useState(false);
  const weekId = useId();
  const semester = semesters[index];
  const all = semesterCourses(semester);
  return (
    <li
      style={
        {
          animationDelay: `${delayMs}ms`,
          "--line-delay": `${delayMs + LINE_DELAY_MS}ms`,
        } as CSSProperties
      }
      className={`relative grid min-w-0 gap-3 before:absolute before:top-7 before:-left-[39px] before:z-[1] before:size-[18px] before:rounded-full before:border-4 before:border-route before:bg-paper after:absolute ${index === 0 ? "after:top-9" : "after:top-0"} after:-bottom-9 after:-left-[32px] after:w-1 after:origin-top after:bg-route motion-safe:animate-rise motion-safe:after:animate-draw motion-safe:after:[animation-delay:var(--line-delay)]`}
    >
      <StationBoard
        index={index}
        semester={semester}
        previous={semesters[index - 1]}
        next={semesters[index + 1]}
      />
      <p className="text-xs text-sub">
        {semester.credits} 単位 ・ {semester.courses.length} 科目
        {semester.continuing.length > 0 &&
          ` ・ ${CONTINUING_LABEL} ${semester.continuing.length} 科目`}
      </p>
      {all.length === 0 && (
        <p className="text-sm text-sub">{EMPTY_SEMESTER_LABEL}</p>
      )}
      {semester.courses.length > 0 && (
        <CourseGrid courses={semester.courses} transfers={transfers} />
      )}
      {semester.continuing.length > 0 && (
        <p className="text-[13px] text-sub">
          {CONTINUING_LABEL}:{" "}
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
            className={TEXT_LINK}
          >
            {open ? "この学期の時間割を閉じる ▴" : "この学期の時間割を開く ▾"}
          </button>
          {planPath && (
            <QueryLink
              href={resultViewHref(
                planPath,
                "timetable",
                semesterKey(semester),
              )}
              onNavigate={() =>
                document.getElementById(VIEWS_ANCHOR)?.scrollIntoView()
              }
              className={TEXT_LINK}
            >
              時間割帳で見る →
            </QueryLink>
          )}
        </div>
      )}
      <div
        id={weekId}
        hidden={!open}
        className="min-w-0 rounded-lg border border-line bg-note p-3.5 motion-safe:animate-rise"
      >
        {open && <WeekTable courses={all} />}
      </div>
    </li>
  );
}
