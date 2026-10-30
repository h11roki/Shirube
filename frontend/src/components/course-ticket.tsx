"use client";

import { useContext } from "react";

import { useCourseWords } from "@/components/course-words";
import { Phrases } from "@/components/phrases";
import { RELEVANCE_TONES } from "@/components/relevance-tones";
import {
  COURSE_TICKET_NOTCH,
  SMALL_BUTTON,
  STANDALONE_LINK,
  TICKET_STAMP,
} from "@/components/styles";
import { TakenAnswersContext } from "@/components/taken-answers";
import { useTransferFocus } from "@/components/transfer-focus";
import type { Course, PlacedCourse } from "@/lib/api/client";
import {
  RELEVANCE_LABELS,
  classLabel,
  markTakenLabel,
  roleLabel,
  slotsLabel,
  syllabusLinkLabel,
  transferLabel,
} from "@/lib/labels";
import type { Transfer } from "@/lib/roadmap";

const EMPHASIS = {
  self: "ring-2 ring-ink/20",
  linked:
    "ring-2 ring-route shadow-[0_0_0_6px_color-mix(in_srgb,var(--route)_18%,transparent)]",
};

function ticketId(section: string): string {
  return `ticket-${section}`;
}

export function revealTicket(section: string) {
  document
    .getElementById(ticketId(section))
    ?.scrollIntoView({ block: "center" });
}

export function CourseTicket({
  course,
  transfer,
}: {
  course: Course | PlacedCourse;
  transfer?: Transfer;
}) {
  const focusing = useTransferFocus();
  const answering = useContext(TakenAnswersContext);
  const nameWords = useCourseWords(course.name);
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
      id={placed ? ticketId(course.section_code) : undefined}
      onPointerEnter={() => focusing?.hover(course.name)}
      onPointerLeave={() => focusing?.hover(null)}
      onFocus={() => focusing?.select(course.name)}
      onBlur={() => focusing?.select(null)}
      className={`relative grid min-w-0 rounded-md border border-line bg-note shadow-paper transition-shadow duration-300 sm:grid-cols-[minmax(0,1fr)_auto] ${emphasis}`}
    >
      <div className="grid min-w-0 content-start gap-1 px-3.5 py-3">
        <p
          className={`text-label font-bold tracking-[0.14em] ${RELEVANCE_TONES[course.relevance].text}`}
        >
          {transfer ? RELEVANCE_LABELS.foundation : roleLabel(course)}
        </p>
        <h3 className={`leading-snug font-bold ${core ? "pr-10" : ""}`}>
          <Phrases parts={nameWords} />
        </h3>
        <p className="text-fine leading-relaxed text-sub">{course.reason}</p>
        {course.syllabus_url && (
          <a
            href={course.syllabus_url}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={syllabusLinkLabel(course.name)}
            className={`justify-self-start text-xs ${STANDALONE_LINK}`}
          >
            <span>
              シラバス
              <span aria-hidden> ↗</span>
            </span>
          </a>
        )}
        {transfer && (
          <p className="text-xs text-route">
            {focusing?.reachable(transfer) ? (
              <button
                type="button"
                onClick={() => focusing.follow(course.name, transfer)}
                className="min-h-6 text-left underline underline-offset-4"
              >
                {transferLabel(transfer)}
              </button>
            ) : (
              transferLabel(transfer)
            )}
          </p>
        )}
        {answering?.asked.has(course.name) && (
          <button
            type="button"
            disabled={answering.busy}
            onClick={() => {
              focusing?.hover(null);
              focusing?.select(null);
              answering.answer(course.name, "mark");
            }}
            aria-label={markTakenLabel(course.name)}
            className={`mt-1 justify-self-start bg-sheet ${SMALL_BUTTON}`}
          >
            もう取った
          </button>
        )}
      </div>
      {placed && (
        <dl
          className={`relative grid content-center gap-1.5 border-dashed border-line px-2 py-3 text-center tabular-nums max-sm:grid-cols-3 max-sm:border-t-2 max-sm:py-2 sm:w-[4.75rem] sm:border-l-2 ${COURSE_TICKET_NOTCH}`}
        >
          <div>
            <dt className="text-label tracking-[0.14em] text-sub">コマ</dt>
            <dd className="text-sm font-bold">{slotsLabel(course)}</dd>
          </div>
          <div>
            <dt className="text-label tracking-[0.14em] text-sub">クラス</dt>
            <dd className="text-sm font-bold">
              {course.class_code === null ? "—" : classLabel(course.class_code)}
              {!course.class_confirmed && (
                <span className="block text-label font-medium text-pillar">
                  未確定
                </span>
              )}
            </dd>
          </div>
          <div>
            <dt className="text-label tracking-[0.14em] text-sub">単位</dt>
            <dd className="text-sm font-bold">{course.credits}</dd>
          </div>
        </dl>
      )}
      {core && (
        <span
          aria-hidden
          className={`right-3 size-9 ${TICKET_STAMP} ${placed ? "sm:right-[5.6rem]" : ""}`}
        >
          {RELEVANCE_LABELS.core}
        </span>
      )}
    </article>
  );
}
