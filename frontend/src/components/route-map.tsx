"use client";

import {
  type CSSProperties,
  type ReactNode,
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from "react";

import { CourseGrid } from "@/components/course-grid";
import { QueryLink } from "@/components/query-link";
import { StationBoard } from "@/components/station-board";
import { TEXT_LINK } from "@/components/styles";
import {
  TransferFocusContext,
  useTransferFocusValue,
} from "@/components/transfer-focus";
import { WeekTable } from "@/components/week-table";
import type { SemesterPlan } from "@/lib/api/client";
import {
  CONTINUING_LABEL,
  EMPTY_SEMESTER_LABEL,
  goalStationLabel,
  semesterShortLabel,
  slotsLabel,
  stationLabel,
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
const IN_VIEW = 0.4;

export function RouteMap({
  semesters,
  shown = semesters.length,
  planPath,
  withStrip = false,
  end,
}: {
  semesters: SemesterPlan[];
  shown?: number;
  planPath?: string;
  withStrip?: boolean;
  end: ReactNode;
}) {
  const found = useMemo(() => transfers(semesters), [semesters]);
  const visible = semesters.slice(0, shown);
  const arrive = visible.length * STAGGER_MS;
  const root = useRef<HTMLDivElement>(null);
  const [active, setActive] = useState(0);
  const reachable = useCallback(
    (transfer: Transfer) => transfer.station < shown,
    [shown],
  );
  const go = useCallback((transfer: Transfer) => {
    document
      .getElementById(`ticket-${transfer.pillarSection}`)
      ?.scrollIntoView({ block: "center" });
  }, []);
  const focusing = useTransferFocusValue(found, reachable, go);

  useEffect(() => {
    if (!withStrip) {
      return;
    }
    let frame = requestAnimationFrame(update);
    function update() {
      frame = 0;
      const stations = root.current?.querySelectorAll("[data-station]") ?? [];
      let current = 0;
      stations.forEach((station, index) => {
        if (station.getBoundingClientRect().top < innerHeight * IN_VIEW) {
          current = index;
        }
      });
      const bottom =
        scrollY + innerHeight >= document.documentElement.scrollHeight - 2;
      setActive(bottom ? stations.length - 1 : current);
    }
    function schedule() {
      if (!frame) {
        frame = requestAnimationFrame(update);
      }
    }
    addEventListener("scroll", schedule, { passive: true });
    addEventListener("resize", schedule);
    return () => {
      cancelAnimationFrame(frame);
      removeEventListener("scroll", schedule);
      removeEventListener("resize", schedule);
    };
  }, [withStrip, visible.length]);

  function pick(index: number) {
    setActive(index);
    root.current
      ?.querySelectorAll("[data-station]")
      [index]?.scrollIntoView({ block: "start" });
  }

  return (
    <TransferFocusContext.Provider value={focusing}>
      <div ref={root} className="grid gap-6">
        {withStrip && (
          <RouteStrip semesters={visible} active={active} onPick={pick} />
        )}
        <ol className="relative grid gap-9 pl-12">
          {visible.map((semester, index) => (
            <Station
              key={semesterKey(semester)}
              index={index}
              semesters={semesters}
              found={found}
              planPath={planPath}
              delayMs={index * STAGGER_MS}
            />
          ))}
          <li
            data-station
            style={
              {
                animationDelay: `${arrive}ms`,
                "--arrive": `${arrive + GOAL_PRESS_MS}ms`,
              } as CSSProperties
            }
            className="relative min-w-0 scroll-mt-28 before:absolute before:top-9 before:-left-[42px] before:z-[1] before:size-6 before:rounded-full before:bg-pillar before:shadow-[0_0_0_4px_var(--paper)] after:absolute after:top-0 after:-left-[32px] after:h-12 after:w-1 after:bg-route motion-safe:animate-rise"
          >
            {end}
          </li>
        </ol>
      </div>
    </TransferFocusContext.Provider>
  );
}

function RouteStrip({
  semesters,
  active,
  onPick,
}: {
  semesters: SemesterPlan[];
  active: number;
  onPick: (index: number) => void;
}) {
  const stops = [
    ...semesters.map((semester, index) => ({
      key: semesterKey(semester),
      station: stationLabel(index),
      name: semesterShortLabel(semester.grade, semester.term),
    })),
    {
      key: "goal",
      station: goalStationLabel(semesters.length),
      name: "卒業",
    },
  ];
  return (
    <nav
      aria-label="路線図"
      className="sticky top-2 z-20 overflow-x-auto rounded-full border border-line bg-sheet/90 px-4 py-2 shadow-paper backdrop-blur"
    >
      <ol className="flex w-max min-w-full items-center justify-between">
        {stops.map((stop, index) => {
          const goal = index === stops.length - 1;
          return (
            <li key={stop.key} className="flex items-center">
              <button
                type="button"
                onClick={() => onPick(index)}
                aria-current={index === active ? "location" : undefined}
                className="grid justify-items-center gap-0.5 px-1.5 text-[11px] leading-tight"
              >
                <span
                  aria-hidden
                  className={`size-3 rounded-full border-2 transition ${goal ? "border-pillar" : "border-route"} ${index <= active ? (goal ? "bg-pillar" : "bg-route") : "bg-sheet"} ${index === active ? "scale-125 shadow-[0_0_0_4px_color-mix(in_srgb,var(--route)_20%,transparent)]" : ""}`}
                />
                <span className="font-bold tabular-nums">{stop.station}</span>
                <span
                  className={`whitespace-nowrap ${index === active ? "text-ink" : "text-sub"}`}
                >
                  {stop.name}
                </span>
              </button>
              {!goal && (
                <span
                  aria-hidden
                  className={`mx-1 h-0.5 w-5 sm:w-12 ${index < active ? "bg-route" : "bg-line"}`}
                />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

function Station({
  index,
  semesters,
  found,
  planPath,
  delayMs,
}: {
  index: number;
  semesters: SemesterPlan[];
  found: Map<string, Transfer>;
  planPath?: string;
  delayMs: number;
}) {
  const [open, setOpen] = useState(false);
  const weekId = useId();
  const semester = semesters[index];
  const all = semesterCourses(semester);
  return (
    <li
      data-station
      style={
        {
          animationDelay: `${delayMs}ms`,
          "--line-delay": `${delayMs + LINE_DELAY_MS}ms`,
        } as CSSProperties
      }
      className={`relative grid min-w-0 scroll-mt-28 gap-3 before:absolute before:top-7 before:-left-[39px] before:z-[1] before:size-[18px] before:rounded-full before:border-4 before:border-route before:bg-paper after:absolute ${index === 0 ? "after:top-9" : "after:top-0"} after:-bottom-9 after:-left-[32px] after:w-1 after:origin-top after:bg-route motion-safe:animate-rise motion-safe:after:animate-draw motion-safe:after:[animation-delay:var(--line-delay)]`}
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
        <CourseGrid courses={semester.courses} transfers={found} />
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
