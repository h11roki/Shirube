"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";

import {
  type ClassChoices,
  type Plan,
  type PlanRequest,
  type Term,
  messageOf,
  requestJson,
} from "@/lib/api/client";
import { TERM_LABELS, classLabel } from "@/lib/labels";

const DEPARTMENT = "情";
const DEPARTMENT_NAME = "電子情報工学科";
const GRADES = [1, 2, 3, 4];
const TERMS: Term[] = ["spring", "autumn"];
const MAX_OCCUPATION_LENGTH = 100;

const fieldClass =
  "w-full rounded-md border border-stone-300 bg-white px-3 py-2 text-stone-900 focus:border-teal-600 focus:outline-none focus:ring-2 focus:ring-teal-600/20";

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
  const [loadError, setLoadError] = useState<string>();
  const [reloads, setReloads] = useState(0);
  const [submitError, setSubmitError] = useState<string>();
  const [submitting, setSubmitting] = useState(false);
  const query = new URLSearchParams({
    department: DEPARTMENT,
    grade: String(grade),
    ...(chosenTerm ? { term: chosenTerm } : {}),
  }).toString();
  const choices = loaded?.query === query ? loaded.answer : undefined;

  useEffect(() => {
    let active = true;
    requestJson<ClassChoices>(`/api/class-choices?${query}`)
      .then((answer) => {
        if (active) {
          setLoaded({ query, answer });
          setLoadError(undefined);
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setLoadError(messageOf(error));
        }
      });
    return () => {
      active = false;
    };
  }, [query, reloads]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setSubmitError(undefined);
    const offered = new Map(
      (choices?.courses ?? []).map((course) => [
        course.name,
        course.class_codes,
      ]),
    );
    const request: PlanRequest = {
      occupation,
      grade,
      term: chosenTerm ?? choices?.term,
      department: DEPARTMENT,
      chosen_classes: Object.fromEntries(
        Object.entries(chosenClasses).filter(([name, code]) =>
          offered.get(name)?.includes(code),
        ),
      ),
    };
    try {
      const plan = await requestJson<Plan>("/api/plans", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });
      router.push(`/plans/${plan.id}`);
    } catch (error) {
      setSubmitError(messageOf(error));
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={submit}
      className="space-y-6 rounded-xl border border-stone-200 bg-white p-6 shadow-sm"
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
            value={chosenTerm ?? choices?.term ?? ""}
            onChange={(event) =>
              setChosenTerm(TERMS.find((value) => value === event.target.value))
            }
          >
            {!chosenTerm && !choices && (
              <option value="">今日の日付から決める</option>
            )}
            {TERMS.map((value) => (
              <option key={value} value={value}>
                {TERM_LABELS[value]}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-2">
          <span className="block text-sm font-medium">学科</span>
          <p className="rounded-md border border-stone-200 bg-stone-50 px-3 py-2 text-stone-700">
            {DEPARTMENT_NAME}
          </p>
        </div>
      </div>

      {loadError && !choices && (
        <div role="alert" className="flex flex-wrap items-center gap-3 text-sm">
          <p className="text-red-700">
            クラスの選択を読み込めませんでした: {loadError}
          </p>
          <button
            type="button"
            onClick={() => setReloads((current) => current + 1)}
            className="rounded-md border border-stone-300 bg-white px-3 py-1 text-stone-800 hover:bg-stone-100"
          >
            読み直す
          </button>
        </div>
      )}

      {choices && choices.courses.length > 0 && (
        <details className="rounded-lg border border-stone-200 bg-stone-50 p-4">
          <summary className="cursor-pointer text-sm font-medium">
            学科でクラスが分かれている科目({choices.courses.length}
            科目、任意)
          </summary>
          <p className="mt-3 text-sm text-stone-600">
            自分のクラスが分かっている科目だけ選んでください。選ばない科目が道標に入ったときは、学科向けのクラスに置き「クラス未確定」と出します。
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {choices.courses.map((course) => {
              const picked = chosenClasses[course.name];
              const index =
                picked === undefined ? -1 : course.class_codes.indexOf(picked);
              return (
                <label key={course.name} className="space-y-1 text-sm">
                  <span className="block text-stone-700">{course.name}</span>
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

      {submitError && (
        <p role="alert" className="text-sm text-red-700">
          {submitError}
        </p>
      )}

      <div className="flex flex-wrap items-center gap-4">
        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-teal-700 px-5 py-2.5 font-medium text-white hover:bg-teal-800 disabled:cursor-not-allowed disabled:bg-stone-400"
        >
          {submitting ? "受け付けています" : "道標を作る"}
        </button>
        <p className="text-xs text-stone-500">
          作るのにふだん 10〜30 秒かかります。
        </p>
      </div>
    </form>
  );
}
