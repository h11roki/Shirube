import { SignInButton } from "@/components/account";
import { CourseWordsProvider } from "@/components/course-words";
import { DestinationPlate } from "@/components/destination-plate";
import { JourneySummary } from "@/components/journey-summary";
import { PlanCaution, SourceNote } from "@/components/plan-caution";
import { RouteMap } from "@/components/route-map";
import { RELEVANCE_LABELS } from "@/lib/labels";
import { STAGGER_MS } from "@/lib/motion";
import { courseNames } from "@/lib/roadmap";
import { SAMPLE_PLAN } from "@/lib/sample-plan";
import { destinationOf, wordsByText } from "@/lib/words";

const SAMPLE_SEMESTERS = 2;
const SAMPLE_DESTINATION = destinationOf(
  SAMPLE_PLAN.result.profile.interpretation,
);
const SAMPLE_COURSE_WORDS = wordsByText(courseNames(SAMPLE_PLAN.result));

const STEPS = [
  {
    title: "職業を入れる",
    detail: "なりたい職業と、いまの回生を入れます。",
  },
  {
    title: "授業を選ぶ",
    detail: `シラバスから、職業の${RELEVANCE_LABELS.core}になる授業と、その${RELEVANCE_LABELS.foundation}になる授業を理由つきで選びます。`,
  },
  {
    title: "卒業までの時間割に並べる",
    detail:
      "コマが重ならず、1 学期の単位の上限に収まるよう、卒業までの学期に並べます。",
  },
];

export function Introduction() {
  const { conditions, result } = SAMPLE_PLAN;
  return (
    <div className="grid gap-12">
      <ol className="relative grid gap-6 sm:grid-cols-3 sm:gap-8">
        {STEPS.map((step, index) => (
          <li
            key={step.title}
            style={{ animationDelay: `${index * STAGGER_MS}ms` }}
            className="relative grid content-start gap-1.5 pl-12 motion-safe:animate-rise sm:pt-12 sm:pl-0"
          >
            <span
              aria-hidden
              className="absolute top-0 left-0 grid size-9 place-items-center rounded-full border-2 border-route bg-paper font-serif text-sm font-extrabold text-route"
            >
              {index + 1}
            </span>
            {index < STEPS.length - 1 && (
              <span
                aria-hidden
                className="absolute top-9 bottom-[-1.5rem] left-[calc(1.125rem-1px)] w-0.5 bg-route sm:top-[calc(1.125rem-1px)] sm:right-[-2rem] sm:bottom-auto sm:left-9 sm:h-0.5 sm:w-auto"
              />
            )}
            <h2 className="font-serif text-lg font-bold">{step.title}</h2>
            <p className="text-sm leading-relaxed text-sub">{step.detail}</p>
          </li>
        ))}
      </ol>

      <section className="grid gap-5">
        <div className="grid gap-1">
          <h2 className="sr-only">{result.profile.interpretation}への道標</h2>
          <div className="flex flex-col items-start justify-self-start sm:flex-row sm:items-stretch">
            <span className="grid place-items-center border border-b-0 border-ink px-2 font-serif text-sm font-semibold tracking-[0.24em] sm:border-r-0 sm:border-b sm:px-1.5 sm:[writing-mode:vertical-rl]">
              見本
            </span>
            <DestinationPlate destination={SAMPLE_DESTINATION} />
          </div>
          <p className="text-sm text-sub">
            {conditions.year}{" "}
            年度の時間割による実際の出力。要約は卒業まで、道のりは初めの{" "}
            {SAMPLE_SEMESTERS} 学期を掲載
          </p>
        </div>
        <PlanCaution />
        <JourneySummary
          semesters={result.semesters}
          conditions={conditions}
          skills={result.profile.skills}
        />
        <CourseWordsProvider words={SAMPLE_COURSE_WORDS}>
          <RouteMap
            semesters={result.semesters}
            shown={SAMPLE_SEMESTERS}
            destination={SAMPLE_DESTINATION}
            endNote="見本はここまでです。ログインすると、自分の職業と回生で作れます。"
          />
        </CourseWordsProvider>
        <SourceNote year={conditions.year} />
      </section>

      <section className="grid justify-items-start gap-4 border border-line bg-sheet p-6 sm:p-8">
        <h2 className="font-serif text-xl font-bold">自分の道標を作ってみる</h2>
        <p className="text-sm text-sub">
          作った道標は保存され、あとから一覧で見返せます。Google
          のアカウントでログインしてください。
        </p>
        <SignInButton />
      </section>
    </div>
  );
}
