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
import { revealTicket } from "@/components/course-ticket";
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
import { VIEWS_ANCHOR, activeStation, resultViewHref } from "@/lib/result-view";

const LINE_DELAY_MS = 250;
const PICK_HOLD_MS = 1200;

export function RouteMap({
  semesters,
  shown = semesters.length,
  planPath,
  withStrip = false,
  destination,
  end,
}: {
  semesters: SemesterPlan[];
  shown?: number;
  planPath?: string;
  withStrip?: boolean;
  destination: string;
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
  const go = useCallback(
    (transfer: Transfer) => revealTicket(transfer.pillarSection),
    [],
  );
  const picked = useRef<ReturnType<typeof setTimeout>>(undefined);
  const focusing = useTransferFocusValue(found, reachable, go);

  useEffect(() => () => clearTimeout(picked.current), []);

  useEffect(() => {
    if (!withStrip) {
      return;
    }
    let frame = requestAnimationFrame(update);
    function update() {
      frame = 0;
      if (picked.current) {
        return;
      }
      const stations = root.current?.querySelectorAll("[data-station]") ?? [];
      const scrolledToEnd =
        scrollY > 0 &&
        scrollY + innerHeight >= document.documentElement.scrollHeight - 2;
      setActive(
        activeStation(
          [...stations].map((station) => station.getBoundingClientRect().top),
          innerHeight,
          scrolledToEnd,
        ),
      );
    }
    function schedule() {
      if (!frame) {
        frame = requestAnimationFrame(update);
      }
    }
    const resized = new ResizeObserver(schedule);
    const area = root.current;
    if (area) {
      resized.observe(area);
      area.addEventListener("animationend", schedule);
    }
    addEventListener("scroll", schedule, { passive: true });
    addEventListener("resize", schedule);
    return () => {
      resized.disconnect();
      area?.removeEventListener("animationend", schedule);
      cancelAnimationFrame(frame);
      removeEventListener("scroll", schedule);
      removeEventListener("resize", schedule);
    };
  }, [withStrip, visible.length]);

  function pick(index: number) {
    setActive(index);
    clearTimeout(picked.current);
    picked.current = setTimeout(() => {
      picked.current = undefined;
    }, PICK_HOLD_MS);
    root.current
      ?.querySelectorAll("[data-station]")
      [index]?.scrollIntoView({ block: "start" });
  }

  return (
    <TransferFocusContext.Provider value={focusing}>
      <div ref={root} className="grid gap-6">
        {withStrip && (
          <RouteStrip
            semesters={visible}
            destination={destination}
            active={active}
            onPick={pick}
          />
        )}
        <ol className="relative grid gap-9 pl-12">
          {visible.map((semester, index) => (
            <Station
              key={semesterKey(semester)}
              index={index}
              semesters={semesters}
              found={found}
              planPath={planPath}
              destination={destination}
              delayMs={index * STAGGER_MS}
            />
          ))}
          <li
            data-station
            style={{ animationDelay: `${arrive}ms` }}
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
  destination,
  active,
  onPick,
}: {
  semesters: SemesterPlan[];
  destination: string;
  active: number;
  onPick: (index: number) => void;
}) {
  const stops = [
    ...semesters.map((semester, index) => ({
      key: semesterKey(semester),
      station: stationLabel(index),
      name: semesterShortLabel(semester.grade, semester.term),
    })),
    { key: "goal", station: null, name: destination },
  ];
  const strip = useRef<HTMLElement>(null);
  useEffect(() => {
    const current = strip.current?.querySelector<HTMLElement>("[aria-current]");
    if (strip.current && current) {
      strip.current.scrollTo({
        left:
          current.offsetLeft -
          (strip.current.clientWidth - current.offsetWidth) / 2,
      });
    }
  }, [active]);
  return (
    <nav
      ref={strip}
      aria-label="路線図"
      className="sticky top-2 z-20 overflow-x-auto rounded-full border border-line bg-sheet/90 px-4 py-2 shadow-paper backdrop-blur"
    >
      <ol className="flex w-max min-w-full items-start justify-between">
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
                {stop.station && (
                  <span className="font-bold tabular-nums">{stop.station}</span>
                )}
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
  destination,
  delayMs,
}: {
  index: number;
  semesters: SemesterPlan[];
  found: Map<string, Transfer>;
  planPath?: string;
  destination: string;
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
        destination={destination}
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
