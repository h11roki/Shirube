import type { PlacedCourse, Weekday } from "@/lib/api/client";

const WEEK: Weekday[] = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
const SCHOOL_DAYS: Weekday[] = ["mon", "tue", "wed", "thu", "fri"];
const MIN_PERIODS = 5;

export type WeekRow = { period: number; cells: PlacedCourse[][] };

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
