import { RELEVANCE_TONES } from "@/components/relevance-tones";
import type { PlacedCourse, Weekday } from "@/lib/api/client";
import {
  PERIOD_HEADER_LABEL,
  PERIOD_SUFFIX,
  RELEVANCE_LABELS,
  WEEKDAY_LABELS,
  WEEKDAY_SUFFIX,
} from "@/lib/labels";
import { halfWidthAlphanumerics } from "@/lib/ticket-face";
import { weekTable } from "@/lib/timetable";

export function WeekTable({ courses }: { courses: PlacedCourse[] }) {
  const table = weekTable(courses);
  return (
    <div className="grid min-w-0 gap-2">
      <table className="w-full table-fixed border-separate border-spacing-1 text-xs sm:border-spacing-1.5">
        <thead>
          <tr>
            <th className="w-9 sm:w-11">
              <span className="sr-only">{PERIOD_HEADER_LABEL}</span>
            </th>
            {table.weekdays.map((weekday) => (
              <th
                key={weekday}
                scope="col"
                className="font-serif font-bold text-sub"
              >
                <WeekdayName weekday={weekday} />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row) => (
            <tr key={row.period}>
              <th
                scope="row"
                className="align-top font-serif font-bold text-sub"
              >
                {row.period}
                <span className="sr-only"> {PERIOD_SUFFIX}</span>
                {row.time && (
                  <span className="mt-0.5 block font-sans text-label font-normal tabular-nums">
                    {row.time.start}
                    <span className="sr-only">から</span>
                    <span className="block">{row.time.end}</span>
                  </span>
                )}
              </th>
              {row.cells.map((cell, index) => (
                <td
                  key={table.weekdays[index]}
                  className={`h-16 align-top ${cell.length === 0 ? "border-[1.5px] border-dashed border-line" : ""}`}
                >
                  {cell.map((course) => (
                    <CourseNote key={course.section_code} course={course} />
                  ))}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {table.unscheduled.length > 0 && (
        <p className="text-xs text-sub">
          コマの無い授業:{" "}
          {table.unscheduled.map((course) => course.name).join("、")}
        </p>
      )}
    </div>
  );
}

function WeekdayName({ weekday }: { weekday: Weekday }) {
  return (
    <>
      <span aria-hidden>{WEEKDAY_LABELS[weekday]}</span>
      <span className="sr-only">
        {WEEKDAY_LABELS[weekday]}
        {WEEKDAY_SUFFIX}
      </span>
    </>
  );
}

function CourseNote({ course }: { course: PlacedCourse }) {
  return (
    <span
      title={course.reason || undefined}
      className={`mb-1 block px-1 py-1 leading-snug font-bold shadow-sticky [overflow-wrap:anywhere] last:mb-0 sm:px-2 sm:py-1.5 ${RELEVANCE_TONES[course.relevance].sticky}`}
    >
      {course.name}
      <span className="mt-0.5 block text-label font-medium text-sub">
        {RELEVANCE_LABELS[course.relevance]}
        {course.room !== null && (
          <>
            {" "}
            <span className="inline-block">
              {halfWidthAlphanumerics(course.room)}
            </span>
          </>
        )}
      </span>
    </span>
  );
}
