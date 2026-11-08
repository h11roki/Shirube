"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState, useTransition } from "react";

import { useApiAnswer } from "@/components/api-answer";
import { FailureNotice } from "@/components/failure-notice";
import { FixedCoursePicker } from "@/components/fixed-course-picker";
import { FIELD, PRIMARY_BUTTON } from "@/components/styles";
import { TakenCourseList } from "@/components/taken-course-list";
import {
  ApiError,
  type ClassChoices,
  type OfferedCourses,
  type PlanRequest,
  type Term,
  UNPROCESSABLE,
  createPlan,
  messageOf,
} from "@/lib/api/client";
import { offeredClasses } from "@/lib/class-choices";
import { chosenCourses, toggledCourses } from "@/lib/fixed-courses";
import {
  DEPARTMENT_NAME,
  OCCUPATION_LABEL,
  TERM_LABELS,
  classChoicesSummary,
  classLabel,
} from "@/lib/labels";
import { MAX_OCCUPATION_LENGTH, occupationProblem } from "@/lib/plan-request";

const DEPARTMENT = "情";
const GRADES = [1, 2, 3, 4];
const TERMS: Term[] = ["spring", "autumn"];

export function PlanForm() {
  const router = useRouter();
  const [occupation, setOccupation] = useState("");
  const [grade, setGrade] = useState(GRADES[0]);
  const [chosenTerm, setChosenTerm] = useState<Term>();
  const [chosenClasses, setChosenClasses] = useState<Record<string, string>>(
    {},
  );
  const [chosenFixed, setChosenFixed] = useState<string[]>([]);
  const [submitError, setSubmitError] = useState<string>();
  const [submitting, setSubmitting] = useState(false);
  const [navigating, startNavigation] = useTransition();
  const busy = submitting || navigating;
  const [takenRefresh, setTakenRefresh] = useState(0);
  const query = new URLSearchParams({
    department: DEPARTMENT,
    grade: String(grade),
    ...(chosenTerm ? { term: chosenTerm } : {}),
  }).toString();
  const classChoices = useApiAnswer<ClassChoices>("/api/class-choices", query);
  const offered = useApiAnswer<OfferedCourses>("/api/offered-courses", query);
  const choices = classChoices.answer;
  const fixedCourses = chosenCourses(offered.answer, chosenFixed);
  const loading = classChoices.loading || offered.loading;
  const term = chosenTerm ?? classChoices.answer?.term;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const refused = occupationProblem(occupation);
    if (refused) {
      setSubmitError(refused);
      return;
    }
    setSubmitting(true);
    setSubmitError(undefined);
    const request: PlanRequest = {
      occupation: occupation.trim(),
      grade,
      term,
      department: DEPARTMENT,
      chosen_classes: offeredClasses(choices, chosenClasses),
      fixed_courses: fixedCourses.map((course) => course.name),
    };
    try {
      const plan = await createPlan(request);
      startNavigation(() => {
        setOccupation("");
        router.push(`/plans/${plan.id}`);
      });
      setSubmitting(false);
    } catch (error) {
      setSubmitError(messageOf(error));
      setSubmitting(false);
      setTakenRefresh((current) => current + 1);
      if (error instanceof ApiError && error.status === UNPROCESSABLE) {
        classChoices.reload();
        offered.reload();
      }
    }
  }

  return (
    <form
      onSubmit={submit}
      className="space-y-6 border border-line bg-sheet p-6 motion-safe:animate-rise sm:p-8"
    >
      <div className="space-y-2">
        <label htmlFor="occupation" className="block text-sm font-medium">
          {OCCUPATION_LABEL}
        </label>
        <input
          id="occupation"
          className={FIELD}
          value={occupation}
          onChange={(event) => setOccupation(event.target.value)}
          required
          maxLength={MAX_OCCUPATION_LENGTH}
          placeholder="例: 組込みエンジニア、データサイエンティスト"
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="space-y-2">
          <label htmlFor="grade" className="block text-sm font-medium">
            いまの回生
          </label>
          <select
            id="grade"
            className={FIELD}
            value={grade}
            onChange={(event) => setGrade(Number(event.target.value))}
          >
            {GRADES.map((value) => (
              <option key={value} value={value}>
                {value} 回生
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-2">
          <label htmlFor="term" className="block text-sm font-medium">
            始める学期
          </label>
          <select
            id="term"
            className={FIELD}
            value={term ?? ""}
            onChange={(event) =>
              setChosenTerm(TERMS.find((value) => value === event.target.value))
            }
          >
            {!term && <option value="">既定の学期</option>}
            {TERMS.map((value) => (
              <option key={value} value={value}>
                {TERM_LABELS[value]}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-2">
          <span className="block text-sm font-medium">学科</span>
          <p className="border border-line bg-paper px-3 py-2 text-sub">
            {DEPARTMENT_NAME}
          </p>
        </div>
      </div>

      {offered.failure && (
        <FailureNotice
          lead={
            offered.answer
              ? "先に入れる授業の一覧を読み直せませんでした(前に読んだ一覧のまま選べます): "
              : "先に入れる授業の一覧を読み込めませんでした(このまま送ると先に入れる授業なしで作ります): "
          }
          message={offered.failure}
          onRetry={offered.reload}
          busy={offered.reloading}
        />
      )}

      {offered.answer && offered.answer.courses.length > 0 && (
        <FixedCoursePicker
          courses={offered.answer.courses}
          chosen={fixedCourses}
          onToggle={(name) =>
            setChosenFixed(toggledCourses(fixedCourses, name))
          }
        />
      )}

      {classChoices.failure && (
        <FailureNotice
          lead={
            choices
              ? "クラスの選択を読み直せませんでした(前に読んだ選択のまま選べます): "
              : "クラスの選択を読み込めませんでした(このまま送るとクラスは未確定で置きます): "
          }
          message={classChoices.failure}
          onRetry={classChoices.reload}
          busy={classChoices.reloading}
        />
      )}

      {choices && choices.courses.length > 0 && (
        <details className="border border-line bg-paper p-4">
          <summary className="cursor-pointer py-1 text-sm font-medium">
            {classChoicesSummary(choices.courses.length)}
          </summary>
          <p className="mt-3 text-sm text-sub">
            自分のクラスが分かっている科目だけ選んでください。選ばない科目が道標に入ったときは、学科向けのクラスに置き「クラス未確定」と出します。
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {choices.courses.map((course) => {
              const picked = chosenClasses[course.name];
              const index =
                picked === undefined ? -1 : course.class_codes.indexOf(picked);
              return (
                <label key={course.name} className="space-y-1 text-sm">
                  <span className="block text-sub">{course.name}</span>
                  <select
                    className={FIELD}
                    value={index < 0 ? "" : String(index)}
                    onChange={(event) => {
                      const value = event.target.value;
                      setChosenClasses((current) => {
                        const next = { ...current };
                        if (value === "") {
                          delete next[course.name];
                        } else {
                          next[course.name] = course.class_codes[Number(value)];
                        }
                        return next;
                      });
                    }}
                  >
                    <option value="">まだ決めない</option>
                    {course.class_codes.map((code, position) => (
                      <option key={code} value={String(position)}>
                        {classLabel(code)}
                      </option>
                    ))}
                  </select>
                </label>
              );
            })}
          </div>
        </details>
      )}

      <TakenCourseList
        refresh={takenRefresh}
        onForget={() => {
          setSubmitError(undefined);
          classChoices.reload();
          offered.reload();
        }}
      />

      {submitError && <FailureNotice message={submitError} />}

      <div className="flex flex-wrap items-center gap-4">
        <button
          type="submit"
          disabled={busy || loading}
          className={`px-6 py-2.5 font-bold disabled:cursor-not-allowed disabled:opacity-50 ${PRIMARY_BUTTON}`}
        >
          {busy ? "受け付けています" : "道標を作る"}
        </button>
      </div>
    </form>
  );
}
