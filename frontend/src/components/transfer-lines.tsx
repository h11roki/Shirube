"use client";

import {
  type CSSProperties,
  type RefObject,
  useEffect,
  useMemo,
  useState,
} from "react";

import { findTicket } from "@/components/course-ticket";
import { useTransferFocus } from "@/components/transfer-focus";
import type { SemesterPlan } from "@/lib/api/client";
import { stationLabel } from "@/lib/labels";
import {
  TRANSFER_DELAY_MS,
  TRANSFER_DRAW_MS,
  TRANSFER_FADE_MS,
} from "@/lib/motion";
import {
  type Box,
  type Point,
  roundedPath,
  transferRoute,
} from "@/lib/transfer-lines";

const CORNER_PX = 6;
const TIMING = {
  "--trace-delay": `${TRANSFER_DELAY_MS}ms`,
  "--trace-ms": `${TRANSFER_DRAW_MS}ms`,
  transitionDuration: `${TRANSFER_FADE_MS}ms`,
} as CSSProperties;

type Drawn = {
  focus: string;
  lines: { name: string; path: string; start: Point; end: Point }[];
  away: { name: string; station: number; above: boolean }[];
  coveredTo: number;
};

export function TransferLines({
  area,
  semesters,
  cover,
}: {
  area: RefObject<HTMLElement | null>;
  semesters: SemesterPlan[];
  cover?: RefObject<HTMLElement | null>;
}) {
  const focusing = useTransferFocus();
  const focus = focusing?.focus ?? null;
  const linked = focusing?.linked;
  const stops = useMemo(
    () =>
      new Map(
        semesters.flatMap((semester, station) =>
          semester.courses.map((course) => [
            course.name,
            { section: course.section_code, station },
          ]),
        ),
      ),
    [semesters],
  );
  const [drawn, setDrawn] = useState<Drawn | null>(null);

  useEffect(() => {
    if (focus !== null) {
      return;
    }
    const faded = setTimeout(() => setDrawn(null), TRANSFER_FADE_MS);
    return () => clearTimeout(faded);
  }, [focus]);

  useEffect(() => {
    const box = area.current;
    if (focus === null || !linked || !box) {
      return;
    }
    const current = focus;
    const names = linked;
    const container = box;
    let frame = requestAnimationFrame(measure);
    function measure() {
      frame = 0;
      const origin = container.getBoundingClientRect();
      const within = (rect: DOMRect): Box => ({
        left: rect.left - origin.left,
        top: rect.top - origin.top,
        right: rect.right - origin.left,
        bottom: rect.bottom - origin.top,
      });
      const source = stops.get(current);
      const from = source && findTicket(source.section);
      const grid = from?.parentElement;
      if (!from || !grid) {
        setDrawn(null);
        return;
      }
      const spacing = getComputedStyle(grid);
      const gaps = {
        row: parseFloat(spacing.rowGap),
        column: parseFloat(spacing.columnGap),
      };
      const coveredTo = Math.max(
        cover?.current?.getBoundingClientRect().bottom ?? 0,
        0,
      );
      const start = within(from.getBoundingClientRect());
      const lines: Drawn["lines"] = [];
      const away: Drawn["away"] = [];
      for (const name of names) {
        const stop = stops.get(name);
        const to = stop && findTicket(stop.section);
        if (!stop || !to) {
          continue;
        }
        const rect = to.getBoundingClientRect();
        const points = transferRoute(start, within(rect), gaps);
        lines.push({
          name,
          path: roundedPath(points, CORNER_PX),
          start: points[1],
          end: points[points.length - 2],
        });
        if (rect.bottom < coveredTo || rect.top > innerHeight) {
          away.push({
            name,
            station: stop.station,
            above: rect.bottom < coveredTo,
          });
        }
      }
      setDrawn({ focus: current, lines, away, coveredTo });
    }
    function schedule() {
      if (!frame) {
        frame = requestAnimationFrame(measure);
      }
    }
    const resized = new ResizeObserver(schedule);
    resized.observe(container);
    addEventListener("scroll", schedule, { passive: true });
    addEventListener("resize", schedule);
    return () => {
      cancelAnimationFrame(frame);
      resized.disconnect();
      removeEventListener("scroll", schedule);
      removeEventListener("resize", schedule);
    };
  }, [area, cover, focus, linked, stops]);

  const shown = drawn !== null && drawn.focus === focus;
  return (
    <>
      <svg
        aria-hidden
        data-transfer-lines
        style={TIMING}
        className={`pointer-events-none absolute inset-0 -z-10 size-full overflow-visible transition-opacity ${shown ? "" : "opacity-0"}`}
      >
        {drawn?.lines.map((line) => (
          <g key={`${drawn.focus}-${line.name}`}>
            <path
              d={line.path}
              pathLength={1}
              className="fill-none stroke-route stroke-[2.5] [stroke-dasharray:1] [stroke-linecap:round] motion-safe:animate-trace"
            />
            {(
              [
                [
                  line.start,
                  "motion-safe:[animation-delay:var(--trace-delay)]",
                ],
                [
                  line.end,
                  "motion-safe:[animation-delay:calc(var(--trace-delay)+var(--trace-ms))]",
                ],
              ] as const
            ).map(([point, delay]) => (
              <circle
                key={`${point.x}-${point.y}`}
                cx={point.x}
                cy={point.y}
                r={4}
                className={`origin-center fill-paper stroke-route stroke-2 [transform-box:fill-box] motion-safe:animate-pop ${delay}`}
              />
            ))}
          </g>
        ))}
      </svg>
      {shown &&
        drawn.away.map((target) => (
          <p
            key={target.name}
            aria-hidden
            style={
              target.above
                ? {
                    top: `calc(max(${drawn.coveredTo}px, env(safe-area-inset-top)) + 0.5rem)`,
                  }
                : undefined
            }
            className={`pointer-events-none fixed left-1/2 z-30 max-w-[calc(100vw-2rem)] -translate-x-1/2 border border-route bg-sheet px-3 py-1 text-xs text-route shadow-sticky ${target.above ? "" : "bottom-[max(1rem,env(safe-area-inset-bottom))]"}`}
          >
            {target.above ? "↑" : "↓"} {stationLabel(target.station)}{" "}
            {target.name}
          </p>
        ))}
    </>
  );
}
