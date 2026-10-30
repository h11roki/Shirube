"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useState, useTransition } from "react";

import { FailureNotice } from "@/components/failure-notice";
import { TakenCourseList } from "@/components/taken-course-list";
import {
  type ClassChoices,
  type Plan,
  type PlanRequest,
  type Term,
  messageOf,
  requestJson,
} from "@/lib/api/client";
import { offeredClasses } from "@/lib/class-choices";
import { DEPARTMENT_NAME, TERM_LABELS, classLabel } from "@/lib/labels";

const DEPARTMENT = "情";
const GRADES = [1, 2, 3, 4];
const TERMS: Term[] = ["spring", "autumn"];
const MAX_OCCUPATION_LENGTH = 100;

const fieldClass =
  "w-full rounded-md border border-edge bg-paper px-3 py-2 text-ink";

export function PlanForm() {
  const router = useRouter();
  const [occupation, setOccupation] = useState("");
  const [grade, setGrade] = useState(GRADES[0]);
  const [chosenTerm, setChosenTerm] = useState<Term>();
  const [loaded, setLoaded] = useState<{
    query: string;
    answer: ClassChoices;
  }>();
  const [chosenClasses, setChosenClasses] = useState<Record<string, string>>(
    {},
  );
  const [failed, setFailed] = useState<{ query: string; message: string }>();
  const [reloads, setReloads] = useState(0);
  const [reloadingChoices, setReloadingChoices] = useState(false);
  const [submitError, setSubmitError] = useState<string>();
  const [submitting, setSubmitting] = useState(false);
  const [navigating, startNavigation] = useTransition();
  const [takenRefresh, setTakenRefresh] = useState(0);
  const query = new URLSearchParams({
    department: DEPARTMENT,
    grade: String(grade),
    ...(chosenTerm ? { term: chosenTerm } : {}),
  }).toString();
  const choices = loaded?.query === query ? loaded.answer : undefined;
  const loadError = failed?.query === query ? failed.message : undefined;
  const loading = !choices && !loadError;
  const term = chosenTerm ?? loaded?.answer.term;

  useEffect(() => {
    let active = true;
    requestJson<ClassChoices>(`/api/class-choices?${query}`)
      .then((answer) => {
        if (active) {
          setLoaded({ query, answer });
          setFailed(undefined);
          setReloadingChoices(false);
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setFailed({ query, message: messageOf(error) });
          setReloadingChoices(false);
        }
      });
    return () => {
      active = false;
    };
  }, [query, reloads]);

  function reloadChoices() {
    setReloadingChoices(true);
    setReloads((current) => current + 1);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!occupation.trim()) {
      setSubmitError("なりたい職業を入れてください");
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
    };
    try {
      const plan = await requestJson<Plan>("/api/plans", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });
      startNavigation(() => router.push(`/plans/${plan.id}`));
      setSubmitting(false);
    } catch (error) {
      setSubmitError(messageOf(error));
      setSubmitting(false);
      setTakenRefresh((current) => current + 1);
    }
  }

  return (
    <form
      onSubmit={submit}
      className="space-y-6 rounded-lg border border-line bg-sheet p-6 shadow-paper motion-safe:animate-rise sm:p-8"
    >
      <div className="space-y-2">
        <label htmlFor="occupation" className="block text-sm font-medium">
          なりたい職業
        </label>
        <input
          id="occupation"
          className={fieldClass}
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
            className={fieldClass}
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
            className={fieldClass}
            value={term ?? ""}
            onChange={(event) =>
              setChosenTerm(TERMS.find((value) => value === event.target.value))
            }
          >
            {!term && <option value="">今日の日付から決める</option>}
            {TERMS.map((value) => (
              <option key={value} value={value}>
                {TERM_LABELS[value]}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-2">
          <span className="block text-sm font-medium">学科</span>
          <p className="rounded-md border border-line bg-paper px-3 py-2 text-sub">
            {DEPARTMENT_NAME}
          </p>
        </div>
      </div>

      {loadError && (
        <FailureNotice
          lead="クラスの選択を読み込めませんでした(このまま送るとクラスは未確定で置きます): "
          message={loadError}
          onRetry={reloadChoices}
          busy={reloadingChoices}
        />
      )}

      {choices && choices.courses.length > 0 && (
        <details className="rounded-lg border border-line bg-paper p-4">
          <summary className="cursor-pointer py-1 text-sm font-medium">
            学科でクラスが分かれている科目({choices.courses.length}
            科目、任意)
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
                    className={fieldClass}
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
          reloadChoices();
        }}
      />

      {submitError && <FailureNotice message={submitError} />}

      <div className="flex flex-wrap items-center gap-4">
        <button
          type="submit"
          disabled={submitting || navigating || loading}
          className="rounded-full bg-pillar px-6 py-2.5 font-bold text-paper hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {submitting || navigating ? "受け付けています" : "道標を作る"}
        </button>
      </div>
    </form>
  );
}
