"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";

import { CourseCard } from "@/components/course-card";
import { Kicker } from "@/components/kicker";
import { QueryLink } from "@/components/query-link";
import { RELEVANCES, RELEVANCE_TONES } from "@/components/relevance-tones";
import { RouteMap } from "@/components/route-map";
import { Signpost } from "@/components/signpost";
import { TimetableBook } from "@/components/timetable-book";
import type { Plan, PlanResult as Result } from "@/lib/api/client";
import {
  RELEVANCE_LABELS,
  RESULT_VIEW_LABELS,
  semesterLabel,
} from "@/lib/labels";
import { routeTotals } from "@/lib/roadmap";
import {
  type ResultView,
  VIEWS_ANCHOR,
  readResultView,
  resultViewHref,
} from "@/lib/result-view";

const VIEWS: ResultView[] = ["route", "timetable"];

export function PlanResultView({
  plan,
  result,
}: {
  plan: Plan;
  result: Result;
}) {
  const pathname = usePathname();
  const { view, semester } = readResultView(useSearchParams());
  const { profile } = result;
  const { conditions } = plan;
  const last = result.semesters.at(-1);
  const totals = routeTotals(result.semesters);
  return (
    <div className="grid gap-8">
      <section className="grid gap-5 sm:grid-cols-[1fr_auto] sm:items-end">
        <div className="grid min-w-0 gap-2">
          <Kicker>目的地 ── {profile.occupation}</Kicker>
          <h1 className="font-serif text-3xl leading-snug font-extrabold text-balance sm:text-4xl">
            {profile.interpretation}への道標
          </h1>
          {profile.assumption && (
            <p className="text-sm text-sub">前提: {profile.assumption}</p>
          )}
          <ul className="flex flex-wrap gap-x-4 gap-y-1 text-[13px] text-sub">
            {profile.skills.map((skill) => (
              <li key={skill}>
                <span aria-hidden className="text-pillar">
                  ◇{" "}
                </span>
                {skill}
              </li>
            ))}
          </ul>
          <p className="text-xs text-sub">
            {[
              ...(last
                ? [
                    `${semesterLabel(conditions.grade, conditions.term)}から ${semesterLabel(last.grade, last.term)}まで`,
                  ]
                : []),
              `1 学期 ${conditions.credit_limit} 単位まで`,
              `${conditions.year} 年度の時間割`,
            ].join(" ・ ")}
          </p>
        </div>
        <Signpost
          from={`${conditions.grade} 回生`}
          className="hidden w-24 text-ink sm:block"
        />
      </section>

      <div
        id={VIEWS_ANCHOR}
        className="flex scroll-mt-4 flex-wrap items-center justify-between gap-3"
      >
        <nav
          aria-label="見え方"
          className="inline-flex rounded-full border border-line bg-sheet p-0.5 text-sm"
        >
          {VIEWS.map((each) => (
            <QueryLink
              key={each}
              href={resultViewHref(pathname, each, semester)}
              aria-current={view === each ? "page" : undefined}
              className={`rounded-full px-4 py-1 ${view === each ? "bg-ink text-paper" : "text-sub hover:text-ink"}`}
            >
              {RESULT_VIEW_LABELS[each]}
            </QueryLink>
          ))}
        </nav>
        <p className="flex gap-4 text-xs text-sub">
          {RELEVANCES.map((relevance) => (
            <span key={relevance} className="flex items-center gap-1.5">
              <span
                aria-hidden
                className={`size-2.5 rounded-xs ${RELEVANCE_TONES[relevance].fill}`}
              />
              {RELEVANCE_LABELS[relevance]}の授業
            </span>
          ))}
        </p>
      </div>

      {view === "route" ? (
        <RouteMap
          semesters={result.semesters}
          planPath={pathname}
          end={
            <>
              <h2 className="font-serif text-xl font-bold">卒業</h2>
              <p className="text-sm text-sub">
                ここまで {totals.credits} 単位。{RELEVANCE_LABELS.core}{" "}
                {totals.core} 科目と{RELEVANCE_LABELS.foundation}{" "}
                {totals.foundation} 科目を通ります。
              </p>
            </>
          }
        />
      ) : (
        <TimetableBook
          semesters={result.semesters}
          selected={semester}
          planPath={pathname}
        />
      )}

      {result.unplaced.length > 0 && (
        <section className="grid gap-3">
          <h2 className="font-serif text-lg font-bold">置けなかった授業</h2>
          <p className="text-sm text-sub">
            残りの学期で、コマが空いていて単位の上限にも収まるクラスが見つからなかった授業です。
          </p>
          <div className="grid gap-2.5 sm:grid-cols-[repeat(auto-fill,minmax(15rem,1fr))]">
            {result.unplaced.map((course) => (
              <CourseCard key={course.name} course={course} />
            ))}
          </div>
        </section>
      )}

      {result.unlinked.length > 0 && (
        <section className="grid gap-3">
          <h2 className="font-serif text-lg font-bold">
            {RELEVANCE_LABELS.core}につながらず外した
            {RELEVANCE_LABELS.foundation}
          </h2>
          <ul className="grid gap-2 text-sm">
            {result.unlinked.map((course) => (
              <li key={course.name}>
                <span className="font-bold">{course.name}</span>
                {course.prerequisite_for && (
                  <span className="text-sub">
                    (→ {course.prerequisite_for})
                  </span>
                )}
                : {course.reason}
              </li>
            ))}
          </ul>
        </section>
      )}

      <p>
        <Link
          href="/"
          className="text-sm text-route underline underline-offset-4"
        >
          別の職業で作る
        </Link>
      </p>
    </div>
  );
}
