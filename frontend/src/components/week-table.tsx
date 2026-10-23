import { RELEVANCE_TONES } from "@/components/relevance-tones";
import type { PlacedCourse, Weekday } from "@/lib/api/client";
import {
  NO_LESSONS_LABEL,
  PERIOD_HEADER_LABEL,
  PERIOD_SUFFIX,
  RELEVANCE_LABELS,
  WEEKDAY_LABELS,
  WEEKDAY_SUFFIX,
  classLabel,
} from "@/lib/labels";
import { daySchedules, weekTable } from "@/lib/timetable";

export function WeekTable({ courses }: { courses: PlacedCourse[] }) {
  const table = weekTable(courses);
  return (
    <div className="grid min-w-0 gap-2">
      <table className="hidden w-full table-fixed border-separate border-spacing-1.5 text-xs sm:table">
        <thead>
          <tr>
            <th className="w-6">
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
              <th scope="row" className="font-serif font-bold text-sub">
                {row.period}
                <span className="sr-only"> {PERIOD_SUFFIX}</span>
              </th>
              {row.cells.map((cell, index) => (
                <td
                  key={table.weekdays[index]}
                  className={`h-14 align-top ${cell.length === 0 ? "rounded-md border-[1.5px] border-dashed border-line" : ""}`}
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
      <dl className="grid gap-1.5 text-xs sm:hidden">
        {daySchedules(table).map((day) => (
          <div
            key={day.weekday}
            className="grid grid-cols-[1.5rem_minmax(0,1fr)] items-start gap-2"
          >
            <dt className="pt-1.5 text-center font-serif font-bold text-sub">
              <WeekdayName weekday={day.weekday} />
            </dt>
            <dd className="grid gap-1">
              {day.lessons.length === 0 ? (
                <span className="rounded-md border-[1.5px] border-dashed border-line px-2 py-1.5 text-sub">
                  {NO_LESSONS_LABEL}
                </span>
              ) : (
                day.lessons.map(({ period, course }) => (
                  <span
                    key={`${period}-${course.section_code}`}
                    className="grid grid-cols-[2.25rem_minmax(0,1fr)] items-start gap-1.5"
                  >
                    <span className="pt-1.5 font-serif text-sub">
                      {period} {PERIOD_SUFFIX}
                    </span>
                    <CourseNote course={course} />
                  </span>
                ))
              )}
            </dd>
          </div>
        ))}
      </dl>
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
      title={course.reason}
      className={`mb-1 block rounded-sm px-2 py-1.5 leading-snug font-bold shadow-sticky [overflow-wrap:anywhere] last:mb-0 ${RELEVANCE_TONES[course.relevance].sticky}`}
    >
      {course.name}
      <span className="mt-0.5 block text-[11px] font-medium text-sub">
        {RELEVANCE_LABELS[course.relevance]}
        {course.class_code !== null && ` ・ ${classLabel(course.class_code)}`}
      </span>
    </span>
  );
}
