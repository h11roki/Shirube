"use client";

import {
  type CSSProperties,
  type RefObject,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { findTicket } from "@/components/course-ticket";
import { useTransferFocus } from "@/components/transfer-focus";
import type { SemesterPlan } from "@/lib/api/client";
import { stationLabel } from "@/lib/labels";
import { courseStops } from "@/lib/roadmap";
import {
  TRANSFER_DELAY_MS,
  TRANSFER_DRAW_MS,
  TRANSFER_FADE_MS,
} from "@/lib/motion";
import {
  type Box,
  type Point,
  offscreenSide,
  roundedPath,
  transferRoute,
} from "@/lib/transfer-lines";

const CORNER_PX = 6;
const TIMING = {
  "--trace-delay": `${TRANSFER_DELAY_MS}ms`,
  "--trace-ms": `${TRANSFER_DRAW_MS}ms`,
  transitionDuration: `${TRANSFER_FADE_MS}ms`,
} as CSSProperties;
const TICKET_GRID = "[data-ticket-grid]";
const BADGE =
  "border border-route bg-sheet px-3 py-1 text-xs text-route shadow-sticky";

type Target = { name: string; station: number; element: HTMLElement };

type Drawn = {
  focus: string;
  lines: { name: string; path: string; start: Point; end: Point }[];
};

type Away = {
  focus: string;
  coveredTo: number;
  above: Target[];
  below: Target[];
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
  const stops = useMemo(() => courseStops(semesters), [semesters]);
  const canvas = useRef<SVGSVGElement>(null);
  const [drawn, setDrawn] = useState<Drawn | null>(null);
  const [away, setAway] = useState<Away | null>(null);

  const shown = drawn !== null && drawn.focus === focus;

  useEffect(() => {
    if (shown) {
      return;
    }
    const faded = setTimeout(() => setDrawn(null), TRANSFER_FADE_MS);
    return () => clearTimeout(faded);
  }, [shown]);

  useEffect(() => {
    const container = area.current;
    if (focus === null || !linked || linked.size === 0 || !container) {
      return;
    }
    const current = focus;
    const names = linked;
    const box = container;
    let targets: Target[] = [];
    let placed = "";
    let measuring = requestAnimationFrame(measure);
    let placing = 0;

    function measure() {
      measuring = 0;
      const origin = box.getBoundingClientRect();
      const within = (rect: DOMRect): Box => ({
        left: rect.left - origin.left,
        top: rect.top - origin.top,
        right: rect.right - origin.left,
        bottom: rect.bottom - origin.top,
      });
      const source = stops.get(current);
      const from = source && findTicket(source.section);
      const grid = from?.closest<HTMLElement>(TICKET_GRID);
      if (!from || !grid) {
        targets = [];
        setDrawn(null);
        place();
        return;
      }
      const spacing = getComputedStyle(grid);
      const gaps = {
        row: parseFloat(spacing.rowGap) || 0,
        column: parseFloat(spacing.columnGap) || 0,
      };
      const gutter =
        within(grid.getBoundingClientRect()).left - gaps.column / 2;
      const start = within(from.getBoundingClientRect());
      targets = [...names].flatMap((name) => {
        const stop = stops.get(name);
        const element = stop && findTicket(stop.section);
        return stop && element
          ? [{ name, station: stop.station, element }]
          : [];
      });
      setDrawn({
        focus: current,
        lines: targets.map(({ name, element }) => {
          const points = transferRoute(
            start,
            within(element.getBoundingClientRect()),
            {
              gaps,
              gutter,
              sameGrid: element.closest(TICKET_GRID) === grid,
            },
          );
          return {
            name,
            path: roundedPath(points, CORNER_PX),
            start: points[1],
            end: points[points.length - 2],
          };
        }),
      });
      place();
    }

    function place() {
      placing = 0;
      const coveredTo = Math.max(
        cover?.current?.getBoundingClientRect().bottom ?? 0,
        0,
      );
      const showing =
        offscreenSide(box.getBoundingClientRect(), coveredTo, innerHeight) ===
        null;
      const sides = showing
        ? targets.map((target) => ({
            target,
            side: offscreenSide(
              target.element.getBoundingClientRect(),
              coveredTo,
              innerHeight,
            ),
          }))
        : [];
      const above = sides.filter(({ side }) => side === "above");
      const below = sides.filter(({ side }) => side === "below");
      const signature = JSON.stringify([
        above.map(({ target }) => target.name),
        below.map(({ target }) => target.name),
        above.length > 0 ? Math.round(coveredTo) : 0,
      ]);
      if (signature === placed) {
        return;
      }
      placed = signature;
      setAway({
        focus: current,
        coveredTo,
        above: above.map(({ target }) => target),
        below: below.map(({ target }) => target),
      });
    }

    function remeasure() {
      if (!measuring) {
        measuring = requestAnimationFrame(measure);
      }
    }
    function replace() {
      if (!placing) {
        placing = requestAnimationFrame(place);
      }
    }
    function settled(event: AnimationEvent) {
      if (!canvas.current?.contains(event.target as Node)) {
        remeasure();
      }
    }
    const resized = new ResizeObserver(remeasure);
    resized.observe(box);
    box.addEventListener("animationend", settled);
    addEventListener("resize", remeasure);
    addEventListener("scroll", replace, { passive: true });
    return () => {
      cancelAnimationFrame(measuring);
      cancelAnimationFrame(placing);
      resized.disconnect();
      box.removeEventListener("animationend", settled);
      removeEventListener("resize", remeasure);
      removeEventListener("scroll", replace);
    };
  }, [area, cover, focus, linked, stops]);

  const badges = shown && away?.focus === focus ? away : null;
  return (
    <>
      <svg
        ref={canvas}
        aria-hidden
        data-transfer-lines
        style={TIMING}
        className={`pointer-events-none absolute inset-0 size-full overflow-visible motion-safe:transition-opacity ${shown ? "" : "opacity-0"}`}
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
                  "start",
                  line.start,
                  "motion-safe:[animation-delay:var(--trace-delay)]",
                ],
                [
                  "end",
                  line.end,
                  "motion-safe:[animation-delay:calc(var(--trace-delay)+var(--trace-ms))]",
                ],
              ] as const
            ).map(([end, point, delay]) => (
              <circle
                key={end}
                cx={point.x}
                cy={point.y}
                r={4}
                className={`origin-center fill-paper stroke-route stroke-2 [transform-box:fill-box] motion-safe:animate-pop ${delay}`}
              />
            ))}
          </g>
        ))}
      </svg>
      {badges && badges.above.length > 0 && (
        <div
          aria-hidden
          style={{
            top: `calc(max(${badges.coveredTo}px, env(safe-area-inset-top)) + 0.5rem)`,
          }}
          className="pointer-events-none fixed left-1/2 z-20 grid max-w-[calc(100vw-2rem)] -translate-x-1/2 justify-items-center gap-1"
        >
          {badges.above.map((target) => (
            <p key={target.name} className={BADGE}>
              ↑ {stationLabel(target.station)} {target.name}
            </p>
          ))}
        </div>
      )}
      {badges && badges.below.length > 0 && (
        <div
          aria-hidden
          className="pointer-events-none fixed bottom-[calc(max(1rem,env(safe-area-inset-bottom))+3.5rem)] left-1/2 z-20 grid max-w-[calc(100vw-2rem)] -translate-x-1/2 justify-items-center gap-1"
        >
          {badges.below.map((target) => (
            <p key={target.name} className={BADGE}>
              ↓ {stationLabel(target.station)} {target.name}
            </p>
          ))}
        </div>
      )}
    </>
  );
}
