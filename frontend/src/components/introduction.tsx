import { SignInButton } from "@/components/account";
import { DestinationPlate } from "@/components/destination-plate";
import { JourneySummary } from "@/components/journey-summary";
import { Kicker } from "@/components/kicker";
import { PlanCaution, SourceNote } from "@/components/plan-caution";
import { RouteMap } from "@/components/route-map";
import { RELEVANCE_LABELS, sampleLabel, semesterLabel } from "@/lib/labels";
import { STAGGER_MS } from "@/lib/motion";
import { SAMPLE_PLAN } from "@/lib/sample-plan";
import { destinationOf } from "@/lib/words";

const SAMPLE_SEMESTERS = 2;
const SAMPLE_DESTINATION = destinationOf(
  SAMPLE_PLAN.result.profile.interpretation,
);

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
              className="absolute top-0 left-0 grid size-9 place-items-center rounded-full border-4 border-route bg-paper font-serif text-sm font-extrabold text-route"
            >
              {index + 1}
            </span>
            {index < STEPS.length - 1 && (
              <span
                aria-hidden
                className="absolute top-9 bottom-[-1.5rem] left-[16px] w-1 bg-route sm:top-[16px] sm:right-[-2rem] sm:bottom-auto sm:left-9 sm:h-1 sm:w-auto"
              />
            )}
            <h2 className="font-serif text-lg font-bold">{step.title}</h2>
            <p className="text-sm leading-relaxed text-sub">{step.detail}</p>
          </li>
        ))}
      </ol>

      <section className="grid gap-5">
        <div className="grid gap-1">
          <Kicker>{sampleLabel(conditions.occupation)}</Kicker>
          <h2 className="sr-only">{result.profile.interpretation}への道標</h2>
          <DestinationPlate destination={SAMPLE_DESTINATION} />
          <p className="text-sm text-sub">
            {conditions.year} 年度の時間割から作った、実際の出力です(
            {semesterLabel(conditions.grade, conditions.term)}
            から)。要約は卒業までのもので、道のりは最初の {
              SAMPLE_SEMESTERS
            }{" "}
            学期だけを載せています。
          </p>
        </div>
        <PlanCaution />
        <JourneySummary
          semesters={result.semesters}
          conditions={conditions}
          destination={result.profile.interpretation}
        />
        <RouteMap
          semesters={result.semesters}
          shown={SAMPLE_SEMESTERS}
          destination={SAMPLE_DESTINATION}
          endNote="見本はここまでです。ログインすると、自分の職業と回生で作れます。"
        />
        <SourceNote year={conditions.year} />
      </section>

      <section className="grid justify-items-start gap-4 rounded-lg border border-line bg-sheet p-6 shadow-paper sm:p-8">
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
