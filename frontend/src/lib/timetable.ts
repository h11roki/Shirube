import type { PlacedCourse, Weekday } from "@/lib/api/client";

const WEEK: Weekday[] = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
const SCHOOL_DAYS: Weekday[] = ["mon", "tue", "wed", "thu", "fri"];
const MIN_PERIODS = 5;

export type PeriodTime = { start: string; end: string };

const PERIOD_TIMES: readonly PeriodTime[] = [
  { start: "9:00", end: "10:35" },
  { start: "10:45", end: "12:20" },
  { start: "13:10", end: "14:45" },
  { start: "14:55", end: "16:30" },
  { start: "16:40", end: "18:15" },
  { start: "18:25", end: "20:00" },
  { start: "20:10", end: "21:45" },
];

export type WeekRow = {
  period: number;
  time: PeriodTime | null;
  cells: PlacedCourse[][];
};

export type Week = {
  weekdays: Weekday[];
  rows: WeekRow[];
  unscheduled: PlacedCourse[];
};

export function weekTable(courses: PlacedCourse[]): Week {
  const slots = courses.flatMap((course) => course.slots);
  const used = new Set(slots.map((slot) => slot.weekday));
  const weekdays = WEEK.filter(
    (weekday) => SCHOOL_DAYS.includes(weekday) || used.has(weekday),
  );
  const lastPeriod = Math.max(MIN_PERIODS, ...slots.map((slot) => slot.period));
  const rows = Array.from({ length: lastPeriod }, (_, index) => index + 1).map(
    (period) => ({
      period,
      time: PERIOD_TIMES.at(period - 1) ?? null,
      cells: weekdays.map((weekday) =>
        courses.filter((course) =>
          course.slots.some(
            (slot) => slot.weekday === weekday && slot.period === period,
          ),
        ),
      ),
    }),
  );
  return {
    weekdays,
    rows,
    unscheduled: courses.filter((course) => course.slots.length === 0),
  };
}

export type DayLesson = {
  period: number;
  time: PeriodTime | null;
  course: PlacedCourse;
};

export type DaySchedule = { weekday: Weekday; lessons: DayLesson[] };

export function daySchedules(table: Week): DaySchedule[] {
  return table.weekdays.map((weekday, index) => ({
    weekday,
    lessons: table.rows.flatMap((row) =>
      row.cells[index].map((course) => ({
        period: row.period,
        time: row.time,
        course,
      })),
    ),
  }));
}
