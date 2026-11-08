import { RELEVANCE_TONES } from "@/components/relevance-tones";
import type { PlacedCourse, Weekday } from "@/lib/api/client";
import {
  CLASS_UNCONFIRMED_LABEL,
  NO_LESSONS_LABEL,
  PERIOD_HEADER_LABEL,
  PERIOD_SUFFIX,
  RELEVANCE_LABELS,
  ROOM_LABEL,
  WEEKDAY_LABELS,
  WEEKDAY_SUFFIX,
} from "@/lib/labels";
import { halfWidthAlphanumerics } from "@/lib/ticket-face";
import {
  type PeriodTime,
  type Week,
  daySchedules,
  weekTable,
} from "@/lib/timetable";

export function WeekTable({ courses }: { courses: PlacedCourse[] }) {
  const table = weekTable(courses);
  return (
    <div className="@container grid min-w-0 gap-2">
      <WeekGrid table={table} />
      <DayList table={table} />
      <Unscheduled table={table} />
    </div>
  );
}

function WeekGrid({ table }: { table: Week }) {
  return (
    <table className="hidden w-full table-fixed border-separate border-spacing-1 text-xs @min-[15rem]:table @md:border-spacing-1.5">
      <thead>
        <tr>
          <th className="w-9 @md:w-11">
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
              {row.time && <PeriodTimes time={row.time} />}
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

function DayList({ table }: { table: Week }) {
  return (
    <dl className="grid gap-1.5 text-xs @min-[15rem]:hidden">
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
              day.lessons.map(({ period, time, course }) => (
                <span
                  key={`${period}-${course.section_code}`}
                  className="grid grid-cols-[2.5rem_minmax(0,1fr)] items-start gap-1.5"
                >
                  <span className="pt-1.5 font-serif text-sub">
                    {period} {PERIOD_SUFFIX}
                    {time && <PeriodTimes time={time} />}
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

function PeriodTimes({ time }: { time: PeriodTime }) {
  return (
    <span className="mt-0.5 block font-sans text-label font-normal tabular-nums">
      {time.start}
      <span className="sr-only">から</span>
      <span className="block">{time.end}</span>
    </span>
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
      className={`mb-1 block px-1 py-1 leading-snug font-bold shadow-sticky [overflow-wrap:anywhere] last:mb-0 @md:px-2 @md:py-1.5 ${RELEVANCE_TONES[course.relevance].sticky}`}
    >
      {course.name}
      <span className="mt-0.5 block text-label font-medium text-sub">
        {RELEVANCE_LABELS[course.relevance]}
        {course.room !== null && (
          <>
            {" "}
            <span className="inline-block">
              <span className="sr-only">{ROOM_LABEL} </span>
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
