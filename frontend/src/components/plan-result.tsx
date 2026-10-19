import Link from "next/link";

import { WeekTable } from "@/components/week-table";
import type {
  Course,
  PlacedCourse,
  Plan,
  PlanResult as Result,
  Relevance,
} from "@/lib/api/client";
import {
  RELEVANCE_LABELS,
  classLabel,
  semesterLabel,
  slotsLabel,
} from "@/lib/labels";

const BADGE_STYLES: Record<Relevance, string> = {
  core: "bg-teal-700 text-white",
  foundation: "bg-amber-100 text-amber-900",
};

function RelevanceBadge({ relevance }: { relevance: Relevance }) {
  return (
    <span
      className={`shrink-0 rounded px-1.5 py-0.5 text-xs font-medium ${BADGE_STYLES[relevance]}`}
    >
      {RELEVANCE_LABELS[relevance]}
    </span>
  );
}

function CourseHeading({ course }: { course: Course }) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <RelevanceBadge relevance={course.relevance} />
      <span className="font-medium">{course.name}</span>
      {course.prerequisite_for && (
        <span className="text-xs text-stone-500">
          → {course.prerequisite_for} の土台
        </span>
      )}
    </div>
  );
}

function PlacedCourseCard({ course }: { course: PlacedCourse }) {
  return (
    <li className="rounded-lg border border-stone-200 bg-white p-3">
      <CourseHeading course={course} />
      <p className="mt-1.5 text-sm text-stone-700">{course.reason}</p>
      <p className="mt-1.5 text-xs text-stone-500">
        {[
          slotsLabel(course),
          ...(course.class_code === null
            ? []
            : [`クラス ${classLabel(course.class_code)}`]),
          ...(course.class_confirmed ? [] : ["クラス未確定"]),
          `${course.credits} 単位`,
        ].join("・")}
      </p>
    </li>
  );
}

export function PlanResultView({
  plan,
  result,
}: {
  plan: Plan;
  result: Result;
}) {
  const { profile } = result;
  const { conditions } = plan;
  return (
    <div className="space-y-8">
      <section className="space-y-3 rounded-xl border border-stone-200 bg-white p-6 shadow-sm">
        <p className="text-sm text-stone-500">{profile.occupation}</p>
        <h1 className="text-2xl font-bold tracking-tight text-balance">
          {profile.interpretation} への道標
        </h1>
        {profile.assumption && (
          <p className="rounded-md bg-stone-50 px-3 py-2 text-sm text-stone-700">
            前提: {profile.assumption}
          </p>
        )}
        <ul className="flex flex-wrap gap-2">
          {profile.skills.map((skill) => (
            <li
              key={skill}
              className="rounded-full bg-teal-50 px-3 py-1 text-xs text-teal-900"
            >
              {skill}
            </li>
          ))}
        </ul>
        <p className="text-xs text-stone-500">
          {semesterLabel(conditions.grade, conditions.term)}から{" "}
          {semesterLabel(4, "autumn")}まで・1 学期 {conditions.credit_limit}{" "}
          単位まで・{conditions.year} 年度の時間割
        </p>
      </section>

      {result.semesters.map((semester) => (
        <section
          key={`${semester.grade}-${semester.term}`}
          className="space-y-4"
        >
          <h2 className="flex items-baseline gap-3 text-lg font-bold">
            {semesterLabel(semester.grade, semester.term)}
            <span className="text-sm font-normal text-stone-500">
              {semester.credits} 単位
            </span>
          </h2>
          {semester.courses.length + semester.continuing.length === 0 ? (
            <p className="text-sm text-stone-500">
              この学期に置いた科目はありません。
            </p>
          ) : (
            <>
              <WeekTable
                courses={[...semester.courses, ...semester.continuing]}
              />
              <ul className="grid gap-3 sm:grid-cols-2">
                {semester.courses.map((course) => (
                  <PlacedCourseCard key={course.section_code} course={course} />
                ))}
              </ul>
              {semester.continuing.length > 0 && (
                <p className="text-xs text-stone-500">
                  春学期からの続き:{" "}
                  {semester.continuing
                    .map((course) => `${course.name}(${slotsLabel(course)})`)
                    .join("、")}
                </p>
              )}
            </>
          )}
        </section>
      ))}

      {result.unplaced.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-lg font-bold">置けなかった科目</h2>
          <p className="text-sm text-stone-600">
            残りの学期で、コマが空いていて単位の上限にも収まるクラスが見つからなかった科目です。
          </p>
          <ul className="grid gap-3 sm:grid-cols-2">
            {result.unplaced.map((course) => (
              <li
                key={course.name}
                className="rounded-lg border border-dashed border-stone-300 p-3"
              >
                <CourseHeading course={course} />
                <p className="mt-1.5 text-sm text-stone-700">{course.reason}</p>
              </li>
            ))}
          </ul>
        </section>
      )}

      {result.unlinked.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-lg font-bold">中心につながらず外した土台</h2>
          <ul className="space-y-2 text-sm text-stone-700">
            {result.unlinked.map((course) => (
              <li key={course.name}>
                {course.name}
                {course.prerequisite_for && (
                  <span className="text-stone-500">
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
        <Link href="/" className="text-sm text-teal-800 underline">
          別の職業で作る
        </Link>
      </p>
    </div>
  );
}
