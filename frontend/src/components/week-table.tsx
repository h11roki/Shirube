import { RELEVANCE_TONES } from "@/components/relevance-tones";
import type { PlacedCourse, Weekday } from "@/lib/api/client";
import {
  CLASS_UNCONFIRMED_LABEL,
  NO_LESSONS_LABEL,
  PERIOD_HEADER_LABEL,
  PERIOD_SUFFIX,
  RELEVANCE_LABELS,
  WEEKDAY_LABELS,
  WEEKDAY_SUFFIX,
} from "@/lib/labels";
import { halfWidthAlphanumerics } from "@/lib/ticket-face";
import { type Week, daySchedules, weekTable } from "@/lib/timetable";

const SWITCHES = {
  "20rem": { grid: "hidden min-[20rem]:table", list: "min-[20rem]:hidden" },
  "40rem": { grid: "hidden sm:table", list: "sm:hidden" },
} as const;

export function WeekTable({
  courses,
  listBelow,
}: {
  courses: PlacedCourse[];
  listBelow: keyof typeof SWITCHES;
}) {
  const table = weekTable(courses);
  const classes = SWITCHES[listBelow];
  return (
    <div className="grid min-w-0 gap-2">
      <WeekGrid table={table} className={classes.grid} />
      <DayList table={table} className={classes.list} />
      <Unscheduled table={table} />
    </div>
  );
}

function WeekGrid({ table, className }: { table: Week; className: string }) {
  return (
    <table
      className={`w-full table-fixed border-separate border-spacing-1 text-xs sm:border-spacing-1.5 ${className}`}
    >
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
            <th scope="row" className="align-top font-serif font-bold text-sub">
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
  );
}

function DayList({ table, className }: { table: Week; className: string }) {
  return (
    <dl className={`grid gap-1.5 text-xs ${className}`}>
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
              <span className="border-[1.5px] border-dashed border-line px-2 py-1.5 text-sub">
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
  );
}

function Unscheduled({ table }: { table: Week }) {
  if (table.unscheduled.length === 0) {
    return null;
  }
  return (
    <p className="text-xs text-sub">
      コマの無い授業:{" "}
      {table.unscheduled.map((course) => course.name).join("、")}
    </p>
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
        {!course.class_confirmed && (
          <span className="block font-bold">{CLASS_UNCONFIRMED_LABEL}</span>
        )}
      </span>
    </span>
  );
}
