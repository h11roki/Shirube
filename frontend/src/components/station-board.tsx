"use client";

import { useEffect, useRef, useState } from "react";

import type { SemesterPlan } from "@/lib/api/client";
import { semesterLabel, semesterReading, stationLabel } from "@/lib/labels";

const SEEN_RATIO = 0.6;

const label = (semester: SemesterPlan) =>
  semesterLabel(semester.grade, semester.term);

export function StationBoard({
  index,
  semester,
  previous,
  next,
  destination,
}: {
  index: number;
  semester: SemesterPlan;
  previous?: SemesterPlan;
  next?: SemesterPlan;
  destination: string;
}) {
  const board = useRef<HTMLDivElement>(null);
  const [seen, setSeen] = useState(false);

  useEffect(() => {
    const target = board.current;
    if (!target) {
      return;
    }
    const watching = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setSeen(true);
          watching.disconnect();
        }
      },
      { threshold: SEEN_RATIO },
    );
    watching.observe(target);
    return () => watching.disconnect();
  }, []);

  return (
    <div
      ref={board}
      className="grid w-full max-w-lg grid-cols-[auto_minmax(0,1fr)] overflow-hidden border border-line bg-sheet"
    >
      <div className="row-span-2 grid place-items-center border-r border-line px-3">
        <span className="grid size-11 place-items-center border-[3px] border-route text-xs font-bold tabular-nums">
          {stationLabel(index)}
        </span>
      </div>
      <div className="grid justify-items-center px-4 pt-2 pb-1.5 text-center">
        <div className="flex flex-wrap items-center justify-center gap-x-2">
          <h2 className="font-serif text-xl font-extrabold tracking-[0.08em] sm:text-2xl">
            {label(semester)}
          </h2>
          {index === 0 && (
            <span className="border border-ink px-1.5 text-label font-bold tracking-[0.12em] text-ink">
              始発
            </span>
          )}
        </div>
        <p className="text-label tracking-[0.3em] text-sub">
          {semesterReading(semester.grade, semester.term)}
        </p>
      </div>
      <span
        aria-hidden
        className={`col-start-2 h-2 origin-left bg-route ${seen ? "motion-safe:animate-band" : "motion-safe:scale-x-0"}`}
      />
      <p className="col-span-2 flex justify-between gap-2 border-t border-line px-3 py-1 text-direction text-sub">
        <span>{previous && `← ${label(previous)}`}</span>
        <span>{next ? label(next) : destination} →</span>
      </p>
    </div>
  );
}
