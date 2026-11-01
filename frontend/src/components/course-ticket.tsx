"use client";

import { type CSSProperties, useContext } from "react";

import { useCourseWords } from "@/components/course-words";
import { Phrases } from "@/components/phrases";
import { RELEVANCE_TONES } from "@/components/relevance-tones";
import {
  COURSE_TICKET_NOTCH,
  SMALL_BUTTON,
  STANDALONE_LINK,
} from "@/components/styles";
import { TakenAnswersContext } from "@/components/taken-answers";
import { TicketStamp } from "@/components/ticket-stamp";
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
import { TEAR_MS } from "@/lib/motion";
import type { Transfer } from "@/lib/roadmap";

const EMPHASIS = {
  self: "ring-2 ring-ink/20",
  linked:
    "ring-2 ring-route shadow-[0_0_0_6px_color-mix(in_srgb,var(--route)_18%,transparent)]",
};

const TORN_PART = "bg-note shadow-[0_0_0_1px_var(--line)]";
const TEARING_AWAY =
  "origin-bottom-left motion-safe:animate-tear [--tear:translate(0.75rem,0.25rem)_rotate(8deg)] max-sm:origin-top-left max-sm:[--tear:translate(0,0.75rem)_rotate(3deg)]";

function ticketId(section: string): string {
  return `ticket-${section}`;
}

export function findTicket(section: string): HTMLElement | null {
  return document.getElementById(ticketId(section));
}

export function revealTicket(section: string) {
  findTicket(section)?.scrollIntoView({ block: "center" });
}

export function CourseTicket({
  course,
  transfer,
  serial,
}: {
  course: Course | PlacedCourse;
  transfer?: Transfer;
  serial?: string;
}) {
  const focusing = useTransferFocus();
  const answering = useContext(TakenAnswersContext);
  const nameWords = useCourseWords(course.name);
  const role = transfer ? RELEVANCE_LABELS.foundation : roleLabel(course);
  const roleShown =
    !transfer &&
    course.relevance === "foundation" &&
    Boolean(course.prerequisite_for);
  const placed = "slots" in course;
  const tearing = answering?.tearing === course.name;
  const ground = RELEVANCE_TONES[course.relevance].ground;
  const torn = tearing ? `${TORN_PART} ${ground}` : "";
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
      style={
        tearing ? ({ "--tear-ms": `${TEAR_MS}ms` } as CSSProperties) : undefined
      }
      className={`relative grid min-w-0 border transition-shadow duration-300 sm:grid-cols-[minmax(0,1fr)_auto] ${tearing ? "border-transparent" : `border-line bg-note ${ground}`} ${emphasis}`}
    >
      <div className={`grid min-w-0 content-start gap-1 px-3.5 py-3 ${torn}`}>
        <p
          className={
            roleShown
              ? `pr-10 text-label font-bold tracking-[0.14em] ${RELEVANCE_TONES[course.relevance].text}`
              : "sr-only"
          }
        >
          {role}
        </p>
        <h3 className="pr-10 leading-snug font-bold">
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
          className={`relative grid content-center gap-1.5 border-dashed border-line px-2 py-3 text-center tabular-nums max-sm:grid-cols-3 max-sm:border-t-2 max-sm:py-2 ${serial ? "pb-6 max-sm:pb-5" : ""} sm:w-[4.75rem] sm:border-l-2 ${COURSE_TICKET_NOTCH} ${tearing ? `${torn} ${TEARING_AWAY}` : ""}`}
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
            <dd className="text-sm font-bold">
              {course.credits}
              {serial && (
                <span
                  aria-hidden
                  className="absolute right-2 bottom-1 text-label font-normal tracking-[0.08em] text-sub"
                >
                  {serial}
                </span>
              )}
            </dd>
          </div>
        </dl>
      )}
      <TicketStamp
        course={course}
        className={`-top-2 right-3 size-9 ${placed ? "sm:right-[5.6rem]" : ""}`}
      />
    </article>
  );
}
