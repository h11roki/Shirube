"use client";

import {
  type CSSProperties,
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from "react";

import { CourseGrid } from "@/components/course-grid";
import { revealTicket } from "@/components/course-ticket";
import { DestinationName } from "@/components/destination-name";
import { Phrases } from "@/components/phrases";
import { QueryLink } from "@/components/query-link";
import { StationBoard } from "@/components/station-board";
import { DESTINATION_TEXT, STANDALONE_LINK } from "@/components/styles";
import { TransferLines } from "@/components/transfer-lines";
import {
  TransferFocusContext,
  useTransferFocusValue,
} from "@/components/transfer-focus";
import { WeekTable } from "@/components/week-table";
import type { SemesterPlan } from "@/lib/api/client";
import {
  CONTINUING_LABEL,
  EMPTY_SEMESTER_LABEL,
  ROUTE_END_SUFFIX,
  routeEndContinuation,
  semesterShortLabel,
  slotsLabel,
  stationLabel,
} from "@/lib/labels";
import {
  REDUCED_MOTION,
  STAGGER_MS,
  TRANSFER_DELAY_MS,
  TRANSFER_DRAW_MS,
} from "@/lib/motion";
import {
  type Transfer,
  semesterCourses,
  semesterKey,
  ticketSerials,
  transfers,
} from "@/lib/roadmap";
import { VIEWS_ANCHOR, activeStation, resultViewHref } from "@/lib/result-view";
import type { Destination } from "@/lib/words";

const LINE_DELAY_MS = 250;
const PICK_HOLD_MS = 1200;

export function RouteMap({
  semesters,
  shown = semesters.length,
  planPath,
  withStrip = false,
  destination,
  endNote,
}: {
  semesters: SemesterPlan[];
  shown?: number;
  planPath?: string;
  withStrip?: boolean;
  destination: Destination;
  endNote: string;
}) {
  const found = useMemo(() => transfers(semesters), [semesters]);
  const serials = useMemo(() => ticketSerials(semesters), [semesters]);
  const visible = semesters.slice(0, shown);
  const arrive = visible.length * STAGGER_MS;
  const continuation = routeEndContinuation(shown, semesters.length);
  const root = useRef<HTMLDivElement>(null);
  const [active, setActive] = useState(0);
  const reachable = useCallback(
    (transfer: Transfer) => transfer.station < shown,
    [shown],
  );
  const following = useRef<ReturnType<typeof setTimeout>>(undefined);
  const go = useCallback((transfer: Transfer) => {
    clearTimeout(following.current);
    if (matchMedia(REDUCED_MOTION).matches) {
      revealTicket(transfer.pillarSection);
      return;
    }
    following.current = setTimeout(
      () => revealTicket(transfer.pillarSection),
      TRANSFER_DELAY_MS + TRANSFER_DRAW_MS,
    );
  }, []);
  const picked = useRef<ReturnType<typeof setTimeout>>(undefined);
  const focusing = useTransferFocusValue(found, reachable, go);

  useEffect(
    () => () => {
      clearTimeout(picked.current);
      clearTimeout(following.current);
    },
    [],
  );

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
      <div ref={root} className="relative isolate grid gap-6">
        <TransferLines
          area={root}
          semesters={visible}
          labelTop={
            withStrip
              ? "top-[calc(env(safe-area-inset-top)+6rem)]"
              : "top-[calc(env(safe-area-inset-top)+1rem)]"
          }
        />
        {withStrip && (
          <RouteStrip
            semesters={visible}
            destinationWords={destination.words}
            active={active}
            onPick={pick}
          />
        )}
        <ol
          className={`relative grid gap-9 pl-12 ${withStrip ? "**:scroll-mt-28" : ""}`}
        >
          {visible.map((semester, index) => (
            <Station
              key={semesterKey(semester)}
              index={index}
              semesters={semesters}
              found={found}
              serials={serials}
              planPath={planPath}
              destination={destination.name}
              delayMs={index * STAGGER_MS}
            />
          ))}
          <li
            data-station
            style={{ animationDelay: `${arrive}ms` }}
            className="relative min-w-0 before:absolute before:top-9 before:-left-[2.625rem] before:z-[1] before:size-6 before:rounded-full before:bg-pillar before:shadow-[0_0_0_4px_var(--paper)] after:absolute after:top-0 after:-left-8 after:h-12 after:w-1 after:bg-route motion-safe:animate-rise"
          >
            <div className="grid min-h-24 content-center gap-1">
              <h2 className={`font-serif font-bold ${DESTINATION_TEXT}`}>
                <DestinationName words={destination.words}>
                  {ROUTE_END_SUFFIX}
                </DestinationName>
                {continuation && (
                  <>
                    <wbr aria-hidden />
                    <span className="whitespace-nowrap">{continuation}</span>
                  </>
                )}
              </h2>
              <p className="text-sm text-sub">{endNote}</p>
            </div>
          </li>
        </ol>
      </div>
    </TransferFocusContext.Provider>
  );
}

function RouteStrip({
  semesters,
  destinationWords,
  active,
  onPick,
}: {
  semesters: SemesterPlan[];
  destinationWords: readonly string[];
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
      station: null,
      name: <Phrases parts={destinationWords} />,
    },
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
      className="sticky top-2 z-20 scroll-px-6 overflow-x-auto border border-line bg-sheet px-6 py-2"
    >
      <ol className="flex w-max min-w-full items-start justify-between">
        {stops.map((stop, index) => {
          const goal = index === stops.length - 1;
          return (
            <li key={stop.key} className="flex items-start">
              <button
                type="button"
                onClick={() => onPick(index)}
                aria-current={index === active ? "location" : undefined}
                className="grid justify-items-center gap-0.5 px-1.5 text-label leading-tight"
              >
                <span
                  aria-hidden
                  className={`size-3 rounded-full border-2 transition ${goal ? "border-pillar" : "border-route"} ${index <= active ? (goal ? "bg-pillar" : "bg-route") : "bg-sheet"} ${index === active ? "scale-125 shadow-[0_0_0_4px_color-mix(in_srgb,var(--route)_20%,transparent)]" : ""}`}
                />
                {stop.station && (
                  <span className="font-bold tabular-nums">{stop.station}</span>
                )}
                <span
                  className={`${goal ? "line-clamp-3 max-w-[9em] text-center" : "whitespace-nowrap"} ${index === active ? "text-ink" : "text-sub"}`}
                >
                  {stop.name}
                </span>
              </button>
              {!goal && (
                <span
                  aria-hidden
                  className={`mx-1 mt-[0.3125rem] h-0.5 w-5 sm:w-12 ${index < active ? "bg-route" : "bg-line"}`}
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
  serials,
  planPath,
  destination,
  delayMs,
}: {
  index: number;
  semesters: SemesterPlan[];
  found: Map<string, Transfer>;
  serials: Map<string, string>;
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
      className={`relative grid min-w-0 gap-3 before:absolute before:top-7 before:-left-[2.4375rem] before:z-[1] before:size-[1.125rem] before:rounded-full before:border-4 before:border-route before:bg-paper after:absolute ${index === 0 ? "after:top-9" : "after:top-0"} after:-bottom-9 after:-left-8 after:w-1 after:origin-top after:bg-route motion-safe:animate-rise motion-safe:after:animate-draw motion-safe:after:[animation-delay:var(--line-delay)]`}
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
        <CourseGrid
          courses={semester.courses}
          transfers={found}
          serials={serials}
        />
      )}
      {semester.continuing.length > 0 && (
        <p className="text-fine text-sub">
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
            className={STANDALONE_LINK}
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
              className={STANDALONE_LINK}
            >
              時間割帳で見る →
            </QueryLink>
          )}
        </div>
      )}
      <div
        id={weekId}
        hidden={!open}
        className="min-w-0 border border-line bg-note p-3.5 motion-safe:animate-rise"
      >
        {open && <WeekTable courses={all} />}
      </div>
    </li>
  );
}
