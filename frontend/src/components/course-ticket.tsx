"use client";

import { RELEVANCE_TONES } from "@/components/relevance-tones";
import { useTransferFocus } from "@/components/transfer-focus";
import type { Course, PlacedCourse } from "@/lib/api/client";
import {
  RELEVANCE_LABELS,
  classLabel,
  roleLabel,
  semesterLabel,
  slotsLabel,
  stationLabel,
} from "@/lib/labels";
import type { Transfer } from "@/lib/roadmap";

const EMPHASIS = {
  self: "ring-2 ring-ink/20",
  linked:
    "ring-2 ring-route shadow-[0_0_0_6px_color-mix(in_srgb,var(--route)_18%,transparent)]",
};

const NOTCH =
  "before:absolute before:-top-2 before:-left-[9px] before:size-4 before:rounded-full before:border before:border-line before:bg-paper before:[clip-path:inset(50%_0_0_0)] after:absolute after:-bottom-2 after:-left-[9px] after:size-4 after:rounded-full after:border after:border-line after:bg-paper after:[clip-path:inset(0_0_50%_0)]";

function transferLabel(transfer: Transfer): string {
  return `乗換 → ${transfer.pillar}(${stationLabel(transfer.station)} ${semesterLabel(transfer.semester.grade, transfer.semester.term)})`;
}

export function CourseTicket({
  course,
  transfer,
}: {
  course: Course | PlacedCourse;
  transfer?: Transfer;
}) {
  const focusing = useTransferFocus();
  const core = course.relevance === "core";
  const placed = "slots" in course;
  const emphasis =
    focusing?.focus === course.name
      ? EMPHASIS.self
      : focusing?.linked.has(course.name)
        ? EMPHASIS.linked
        : "";
  return (
    <article
      id={placed ? `ticket-${course.section_code}` : undefined}
      onPointerEnter={() => focusing?.hover(course.name)}
      onPointerLeave={() => focusing?.hover(null)}
      onFocus={() => focusing?.hover(course.name)}
      onBlur={() => focusing?.hover(null)}
      className={`relative grid min-w-0 scroll-mt-28 grid-cols-[minmax(0,1fr)_auto] rounded-md border border-line bg-note shadow-paper transition-shadow duration-300 ${emphasis}`}
    >
      <div className="grid min-w-0 content-start gap-1 px-3.5 py-3">
        <p
          className={`text-[11px] font-bold tracking-[0.14em] ${RELEVANCE_TONES[course.relevance].text}`}
        >
          {transfer ? RELEVANCE_LABELS.foundation : roleLabel(course)}
        </p>
        <h3 className={`leading-snug font-bold ${core ? "pr-10" : ""}`}>
          {course.name}
        </h3>
        <p className="text-[13px] leading-relaxed text-sub">{course.reason}</p>
        {transfer && (
          <p className="text-xs text-route">
            {focusing ? (
              <button
                type="button"
                onClick={() => focusing.follow(course.name, transfer)}
                className="text-left underline underline-offset-4"
              >
                {transferLabel(transfer)}
              </button>
            ) : (
              transferLabel(transfer)
            )}
          </p>
        )}
        {transfer && transfer.order !== "before" && (
          <p className="text-xs font-bold text-pillar">
            {RELEVANCE_LABELS.core}
            {transfer.order === "same" ? "と同じ" : "より後の"}学期です
          </p>
        )}
      </div>
      {placed && (
        <dl
          className={`relative grid w-[4.75rem] content-center gap-1.5 border-l-2 border-dashed border-line px-2 py-3 text-center tabular-nums ${NOTCH}`}
        >
          <div>
            <dt className="text-[9.5px] tracking-[0.14em] text-sub">コマ</dt>
            <dd className="text-sm font-bold">{slotsLabel(course)}</dd>
          </div>
          <div>
            <dt className="text-[9.5px] tracking-[0.14em] text-sub">クラス</dt>
            <dd className="text-sm font-bold">
              {course.class_code === null ? "—" : classLabel(course.class_code)}
              {!course.class_confirmed && (
                <span className="block text-[10px] font-medium text-pillar">
                  未確定
                </span>
              )}
            </dd>
          </div>
          <div>
            <dt className="text-[9.5px] tracking-[0.14em] text-sub">単位</dt>
            <dd className="text-sm font-bold">{course.credits}</dd>
          </div>
        </dl>
      )}
      {core && (
        <span
          aria-hidden
          className={`absolute top-2.5 grid size-9 rotate-[-12deg] place-items-center rounded-full border-[2.5px] border-pillar font-serif font-extrabold text-pillar opacity-85 ${placed ? "right-[5.6rem]" : "right-3"}`}
        >
          {RELEVANCE_LABELS.core}
        </span>
      )}
    </article>
  );
}
