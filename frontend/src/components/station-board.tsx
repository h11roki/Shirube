import type { SemesterPlan } from "@/lib/api/client";
import { semesterLabel, semesterReading, stationLabel } from "@/lib/labels";

const label = (semester: SemesterPlan) =>
  semesterLabel(semester.grade, semester.term);

export function StationBoard({
  index,
  semester,
  previous,
  next,
}: {
  index: number;
  semester: SemesterPlan;
  previous?: SemesterPlan;
  next?: SemesterPlan;
}) {
  return (
    <div className="grid w-full max-w-lg grid-cols-[auto_minmax(0,1fr)] overflow-hidden rounded-md border border-line bg-sheet shadow-paper">
      <div className="row-span-2 grid place-items-center border-r border-line px-3">
        <span className="grid size-11 place-items-center rounded-md border-[3px] border-route text-xs font-bold tabular-nums">
          {stationLabel(index)}
        </span>
      </div>
      <div className="grid justify-items-center px-4 pt-2 pb-1.5 text-center">
        <h2 className="font-serif text-xl font-extrabold tracking-[0.08em] sm:text-2xl">
          {label(semester)}
          {index === 0 && (
            <span className="ml-2 inline-block rounded-xs bg-pillar px-1.5 align-[3px] font-sans text-[10.5px] tracking-[0.12em] text-paper">
              始発
            </span>
          )}
        </h2>
        <p className="text-[10.5px] tracking-[0.3em] text-sub">
          {semesterReading(semester.grade, semester.term)}
        </p>
      </div>
      <span aria-hidden className="col-start-2 h-2 bg-route" />
      <p className="col-span-2 flex justify-between gap-2 border-t border-line px-3 py-1 text-[11.5px] text-sub">
        <span>{previous && `← ${label(previous)}`}</span>
        <span>{next ? `${label(next)} →` : "卒業 →"}</span>
      </p>
    </div>
  );
}
