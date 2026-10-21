"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { CourseGrid } from "@/components/course-grid";
import { DeletePlanButton } from "@/components/delete-plan-button";
import { DestinationPlate } from "@/components/destination-plate";
import { JourneySummary } from "@/components/journey-summary";
import { Kicker } from "@/components/kicker";
import { PlanCaution, SourceNote } from "@/components/plan-caution";
import { QueryLink } from "@/components/query-link";
import { RELEVANCES, RELEVANCE_TONES } from "@/components/relevance-tones";
import { RouteMap } from "@/components/route-map";
import { TEXT_LINK } from "@/components/styles";
import { TakenAnswersContext } from "@/components/taken-answers";
import { TimetableBook } from "@/components/timetable-book";
import {
  type Plan,
  type PlanResult as Result,
  messageOf,
  requestJson,
} from "@/lib/api/client";
import {
  RELEVANCE_LABELS,
  RESULT_VIEW_LABELS,
  type TakenChange,
  answeredLabel,
  failedAnswerLabel,
  unmarkTakenLabel,
  semesterLabel,
} from "@/lib/labels";
import {
  type ResultView,
  VIEWS_ANCHOR,
  readResultView,
  resultViewHref,
} from "@/lib/result-view";

const VIEWS: ResultView[] = ["route", "timetable"];
const ANSWERED_MS = 6000;
const TAKEN_METHODS: Record<TakenChange, string> = {
  mark: "PUT",
  unmark: "DELETE",
};

type Answered = { message: string; failed: boolean; undo: string | null };

export function PlanResultView({
  plan,
  result,
  onAnswered,
}: {
  plan: Plan;
  result: Result;
  onAnswered: (plan: Plan) => void;
}) {
  const pathname = usePathname();
  const { view, semester } = readResultView(useSearchParams());
  const [busy, setBusy] = useState(false);
  const [answered, setAnswered] = useState<Answered>();
  const notice = useRef<HTMLDivElement>(null);
  const { profile } = result;
  const { conditions } = plan;
  const last = result.semesters[result.semesters.length - 1];
  const undo = answered?.undo ?? null;

  useEffect(() => {
    if (!answered) {
      return;
    }
    const timer = setTimeout(() => {
      if (notice.current?.contains(document.activeElement)) {
        notice.current.focus({ preventScroll: true });
      }
      setAnswered(undefined);
    }, ANSWERED_MS);
    return () => clearTimeout(timer);
  }, [answered]);

  const planApi = `/api/plans/${encodeURIComponent(plan.id)}`;

  async function reloadFailure(): Promise<string | null> {
    try {
      onAnswered(await requestJson<Plan>(planApi));
      return null;
    } catch (caught) {
      return messageOf(caught);
    }
  }

  async function answer(name: string, change: TakenChange) {
    setBusy(true);
    try {
      onAnswered(
        await requestJson<Plan>(
          `${planApi}/taken-courses/${encodeURIComponent(name)}`,
          { method: TAKEN_METHODS[change] },
        ),
      );
      setAnswered({
        message: answeredLabel(name, change),
        failed: false,
        undo: change === "mark" ? name : null,
      });
    } catch (caught) {
      setAnswered({
        message: failedAnswerLabel(messageOf(caught), await reloadFailure()),
        failed: true,
        undo: null,
      });
    } finally {
      setBusy(false);
      notice.current?.focus({ preventScroll: true });
    }
  }

  return (
    <TakenAnswersContext.Provider
      value={{
        asked: new Set(result.offered_earlier),
        busy,
        answer: (name, change) => void answer(name, change),
      }}
    >
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
          <PlanCaution />
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
          <JourneySummary
            semesters={result.semesters}
            conditions={conditions}
            destination={profile.interpretation}
          />
          <p className="text-xs text-sub">
            1 学期 {conditions.credit_limit} 単位まで ・ {conditions.year}{" "}
            年度の時間割
          </p>
          {result.offered_earlier.length > result.taken.length && (
            <p className="max-w-2xl text-xs text-sub">
              前の学期にも開講された授業は、もう取っていれば切符の「もう取った」を押してください。道標から外して置き直します。
            </p>
          )}
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
            withStrip
            destination={profile.interpretation}
            endNote={`${semesterLabel(last.grade, last.term)}のあと、道標はここで終わります。`}
          />
        ) : (
          <TimetableBook
            semesters={result.semesters}
            selected={semester}
            planPath={pathname}
          />
        )}

        {result.taken.length > 0 && (
          <section className="grid gap-3 rounded-lg border border-line bg-sheet p-4 sm:p-5">
            <h2 className="font-serif text-lg font-bold">もう取った授業</h2>
            <p className="text-sm text-sub">
              もう取ったと答えた授業です。道標から外しています。戻すと、もう一度置き直します。
            </p>
            <ul className="grid gap-2 text-sm">
              {result.taken.map((course) => (
                <li
                  key={course.name}
                  className="flex flex-wrap items-center gap-x-3 gap-y-1"
                >
                  <span
                    className={`text-[11px] font-bold tracking-[0.14em] ${RELEVANCE_TONES[course.relevance].text}`}
                  >
                    {RELEVANCE_LABELS[course.relevance]}
                  </span>
                  <span className="font-bold">{course.name}</span>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void answer(course.name, "unmark")}
                    aria-label={unmarkTakenLabel(course.name)}
                    className="rounded-full border border-line px-3 py-0.5 text-xs text-sub hover:border-ink hover:text-ink disabled:opacity-50"
                  >
                    戻す
                  </button>
                </li>
              ))}
            </ul>
          </section>
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

        <SourceNote year={conditions.year} />
        <div className="flex flex-wrap items-start gap-x-6 gap-y-3">
          <Link href="/" className={`text-sm ${TEXT_LINK}`}>
            別の職業で作る
          </Link>
          <DeletePlanButton id={plan.id} />
        </div>
      </div>
      <div
        ref={notice}
        role="status"
        tabIndex={-1}
        className="pointer-events-none fixed inset-x-0 bottom-[max(1rem,env(safe-area-inset-bottom))] z-30 flex justify-center px-4"
      >
        {answered && (
          <p
            className={`pointer-events-auto flex flex-wrap items-center gap-x-4 gap-y-1 rounded-full border px-5 py-2 text-sm shadow-sticky ${answered.failed ? "border-danger/30 bg-danger-soft text-danger" : "border-line bg-sheet"}`}
          >
            {answered.message}
            {undo && (
              <button
                type="button"
                disabled={busy}
                onClick={() => void answer(undo, "unmark")}
                className={TEXT_LINK}
              >
                戻す
              </button>
            )}
          </p>
        )}
      </div>
    </TakenAnswersContext.Provider>
  );
}
