"use client";

import { useId, useMemo, useRef, useState } from "react";

import { FIELD, SMALL_BUTTON } from "@/components/styles";
import type { OfferedCourse } from "@/lib/api/client";
import { MAX_FIXED_COURSES, matchingCourses } from "@/lib/fixed-courses";
import {
  dropFixedLabel,
  fixedCoursesSummary,
  matchCountLabel,
  offeredCourseNote,
} from "@/lib/labels";

export function FixedCoursePicker({
  courses,
  chosen,
  onToggle,
}: {
  courses: readonly OfferedCourse[];
  chosen: readonly OfferedCourse[];
  onToggle: (name: string) => void;
}) {
  const [filter, setFilter] = useState("");
  const summary = useRef<HTMLElement>(null);
  const chosenHeading = useId();
  const rows = useId();
  const filterInput = useId();
  const chosenNames = new Set(chosen.map((course) => course.name));
  const matches = useMemo(
    () => matchingCourses(courses, filter),
    [courses, filter],
  );
  const full = chosen.length >= MAX_FIXED_COURSES;

  return (
    <details className="border border-line bg-paper p-4">
      <summary
        ref={summary}
        className="cursor-pointer py-1 text-sm font-medium"
      >
        {fixedCoursesSummary(chosen.length)}
      </summary>
      <p className="mt-3 text-sm text-sub">
        必修など取ると決めている授業を選ぶと、推薦の授業より先に時間割へ置き、推薦の候補からは外します。
        {MAX_FIXED_COURSES} 科目まで選べます。
      </p>
      {chosen.length > 0 && (
        <div className="mt-4">
          <p id={chosenHeading} className="text-sm font-medium">
            選んだ授業
          </p>
          <ul aria-labelledby={chosenHeading} className="mt-2 grid gap-2">
            {chosen.map((course) => (
              <li
                key={course.name}
                className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm [overflow-wrap:anywhere]"
              >
                <span className="font-bold">{course.name}</span>
                <span className="text-fine text-sub">
                  {offeredCourseNote(course)}
                </span>
                <button
                  type="button"
                  onClick={() => {
                    onToggle(course.name);
                    summary.current?.focus();
                  }}
                  aria-label={dropFixedLabel(course.name)}
                  className={SMALL_BUTTON}
                >
                  外す
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
      <div className="mt-4 space-y-2">
        <label htmlFor={filterInput} className="block text-sm">
          授業名で絞る
        </label>
        <input
          id={filterInput}
          type="search"
          className={FIELD}
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
            }
          }}
        />
      </div>
      <div aria-live="polite" className="mt-2 space-y-1 text-sm text-sub">
        <p>{matchCountLabel(matches.length)}</p>
        {full && (
          <p>
            選べるのは {MAX_FIXED_COURSES}{" "}
            科目までです。ほかの授業を選ぶときは、先に外してください。
          </p>
        )}
      </div>
      <fieldset className="mt-2 min-w-0 border-y border-line">
        <legend className="sr-only">開講される授業</legend>
        <ul className="focus-room-x max-h-80 overflow-y-auto">
          {matches.map((course, index) => {
            const checked = chosenNames.has(course.name);
            const row = `${rows}-${index}`;
            return (
              <li
                key={course.name}
                className="border-b border-line last:border-b-0"
              >
                <label className="group flex cursor-pointer gap-2 py-2 text-sm has-disabled:cursor-not-allowed has-disabled:text-sub forced-colors:has-disabled:text-[GrayText]">
                  <span className="relative shrink-0 self-start">
                    <input
                      type="checkbox"
                      checked={checked}
                      disabled={full && !checked}
                      onChange={() => onToggle(course.name)}
                      aria-labelledby={`${row}-name`}
                      aria-describedby={`${row}-note`}
                      className="peer block size-6 cursor-[inherit] appearance-none border border-edge bg-paper checked:border-route checked:bg-route enabled:not-checked:group-hover:border-ink disabled:opacity-50 forced-colors:disabled:border-[GrayText] forced-colors:disabled:opacity-100"
                    />
                    <span
                      aria-hidden="true"
                      className="pointer-events-none absolute inset-0 m-auto hidden h-3 w-1.5 -translate-y-0.5 rotate-45 border-r-2 border-b-2 border-paper peer-checked:block"
                    />
                  </span>
                  <span className="min-w-0 [overflow-wrap:anywhere]">
                    <span id={`${row}-name`} className="block">
                      {course.name}
                    </span>
                    <span
                      id={`${row}-note`}
                      className="block text-fine text-sub"
                    >
                      {offeredCourseNote(course)}
                    </span>
                  </span>
                </label>
              </li>
            );
          })}
        </ul>
      </fieldset>
    </details>
  );
}
