import type { PlacedCourse, Weekday } from "@/lib/api/client";

const WEEK: Weekday[] = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
const SCHOOL_DAYS: Weekday[] = ["mon", "tue", "wed", "thu", "fri"];
const MIN_PERIODS = 5;

export type PeriodTime = { start: string; end: string };

const PERIOD_TIMES: Readonly<Record<number, PeriodTime>> = {
  1: { start: "9:00", end: "10:35" },
  2: { start: "10:45", end: "12:20" },
  3: { start: "13:10", end: "14:45" },
  4: { start: "14:55", end: "16:30" },
  5: { start: "16:40", end: "18:15" },
  6: { start: "18:25", end: "20:00" },
  7: { start: "20:10", end: "21:45" },
};

export type WeekRow = {
  period: number;
  time: PeriodTime | null;
  cells: PlacedCourse[][];
};

export type WeekTable = {
  weekdays: Weekday[];
  rows: WeekRow[];
  unscheduled: PlacedCourse[];
};

export function weekTable(courses: PlacedCourse[]): WeekTable {
  const slots = courses.flatMap((course) => course.slots);
  const used = new Set(slots.map((slot) => slot.weekday));
  const weekdays = WEEK.filter(
    (weekday) => SCHOOL_DAYS.includes(weekday) || used.has(weekday),
  );
  const lastPeriod = Math.max(MIN_PERIODS, ...slots.map((slot) => slot.period));
  const rows = Array.from({ length: lastPeriod }, (_, index) => index + 1).map(
    (period) => ({
      period,
      time: PERIOD_TIMES[period] ?? null,
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
