"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";

import { CourseGrid } from "@/components/course-grid";
import { DestinationPlate } from "@/components/destination-plate";
import { JourneySummary } from "@/components/journey-summary";
import { Kicker } from "@/components/kicker";
import { QueryLink } from "@/components/query-link";
import { RELEVANCES, RELEVANCE_TONES } from "@/components/relevance-tones";
import { RouteMap } from "@/components/route-map";
import { TEXT_LINK } from "@/components/styles";
import { TimetableBook } from "@/components/timetable-book";
import type { Plan, PlanResult as Result } from "@/lib/api/client";
import {
  RELEVANCE_LABELS,
  RESULT_VIEW_LABELS,
  goalStationLabel,
  semesterLabel,
} from "@/lib/labels";
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
  return (
    <div className="grid gap-8">
      <section className="grid gap-4">
        <h1 className="sr-only">{profile.interpretation}への道標</h1>
        <Kicker>目的地 ── {profile.occupation}</Kicker>
        <DestinationPlate destination={profile.interpretation} />
        {profile.assumption && (
          <p className="max-w-2xl text-sm text-sub">
            前提: {profile.assumption}
          </p>
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
        <JourneySummary semesters={result.semesters} conditions={conditions} />
        <p className="text-xs text-sub">
          1 学期 {conditions.credit_limit} 単位まで ・ {conditions.year}{" "}
          年度の時間割
        </p>
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
            <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
              <span
                aria-hidden
                className="relative grid size-24 shrink-0 rotate-[-8deg] place-items-center rounded-full border-[3px] border-pillar text-center leading-tight text-pillar before:absolute before:inset-1.5 before:rounded-full before:border-[1.5px] before:border-dashed before:border-pillar motion-safe:animate-press motion-safe:[animation-delay:var(--arrive,0ms)]"
              >
                <span className="grid">
                  <span className="text-[9px] tracking-[0.2em]">しるべ線</span>
                  <span className="font-serif text-2xl font-extrabold tracking-[0.1em]">
                    卒業
                  </span>
                  <span className="text-[9.5px] tracking-[0.1em] tabular-nums">
                    {goalStationLabel(result.semesters.length)}
                  </span>
                </span>
              </span>
              <div className="grid gap-1">
                <h2 className="font-serif text-2xl font-bold">卒業駅</h2>
                {last && (
                  <p className="text-sm text-sub">
                    {semesterLabel(last.grade, last.term)}
                    のあと、道標はここで終わります。
                  </p>
                )}
              </div>
            </div>
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
        <section className="grid gap-3 rounded-lg border border-dashed border-line p-4 sm:p-5">
          <h2 className="font-serif text-lg font-bold">置けなかった授業</h2>
          <p className="text-sm text-sub">
            残りの学期で、コマが空いていて単位の上限にも収まるクラスが見つからなかった授業です。
          </p>
          <CourseGrid courses={result.unplaced} />
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
        <Link href="/" className={`text-sm ${TEXT_LINK}`}>
          別の職業で作る
        </Link>
      </p>
    </div>
  );
}
