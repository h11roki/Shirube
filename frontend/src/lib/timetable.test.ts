import { describe, expect, it } from "vitest";

import type { PlacedCourse } from "@/lib/api/client";
import { daySchedules, weekTable } from "@/lib/timetable";

function course(name: string, slots: PlacedCourse["slots"]): PlacedCourse {
  return {
    name,
    relevance: "core",
    reason: `${name}の理由`,
    prerequisite_for: null,
    syllabus_code: "10000",
    syllabus_url: null,
    section_code: "10000",
    class_code: "6T",
    slots,
    room: "C302",
    credits: 2,
    class_confirmed: true,
  };
}

const FIRST = { start: "9:00", end: "10:35" };
const SECOND = { start: "10:45", end: "12:20" };
const THIRD = { start: "13:10", end: "14:45" };
const SEVENTH = { start: "20:10", end: "21:45" };

describe("weekTable", () => {
  it("lays out Monday to Friday and periods 1 to 5 even for an empty semester", () => {
    const table = weekTable([]);

    expect(table.weekdays).toEqual(["mon", "tue", "wed", "thu", "fri"]);
    expect(table.rows.map((row) => row.period)).toEqual([1, 2, 3, 4, 5]);
    expect(table.rows.flatMap((row) => row.cells.flat())).toEqual([]);
  });

  it("puts each course in every slot it takes", () => {
    const twoSlots = course("科目A", [
      { weekday: "mon", period: 1 },
      { weekday: "mon", period: 2 },
    ]);
    const wednesday = course("科目B", [{ weekday: "wed", period: 1 }]);

    const table = weekTable([twoSlots, wednesday]);

    expect(table.rows[0].cells).toEqual([[twoSlots], [], [wednesday], [], []]);
    expect(table.rows[1].cells[0]).toEqual([twoSlots]);
  });

  it("adds the weekend and later periods only when a course needs them", () => {
    const saturday = course("土曜の科目", [{ weekday: "sat", period: 7 }]);

    const table = weekTable([saturday]);

    expect(table.weekdays).toEqual(["mon", "tue", "wed", "thu", "fri", "sat"]);
    expect(table.rows).toHaveLength(7);
    expect(table.rows[6].cells[5]).toEqual([saturday]);
  });

  it("gives each period the start and end of its class hour", () => {
    const table = weekTable([]);

    expect(table.rows.map((row) => row.time)).toEqual([
      { start: "9:00", end: "10:35" },
      { start: "10:45", end: "12:20" },
      { start: "13:10", end: "14:45" },
      { start: "14:55", end: "16:30" },
      { start: "16:40", end: "18:15" },
    ]);
  });

  it("leaves the time out for a period beyond the seventh", () => {
    const late = course("遅い科目", [{ weekday: "mon", period: 8 }]);

    const table = weekTable([late]);

    expect(table.rows[6].time).toEqual({ start: "20:10", end: "21:45" });
    expect(table.rows[7].time).toBeNull();
  });

  it("keeps courses without slots apart from the grid", () => {
    const intensive = course("集中講義", []);

    const table = weekTable([intensive]);

    expect(table.unscheduled).toEqual([intensive]);
    expect(table.rows.flatMap((row) => row.cells.flat())).toEqual([]);
  });
});

describe("daySchedules", () => {
  it("lists every weekday of the table with its lessons and their times in period order", () => {
    const twoSlots = course("科目A", [
      { weekday: "mon", period: 2 },
      { weekday: "mon", period: 1 },
    ]);
    const wednesday = course("科目B", [{ weekday: "wed", period: 3 }]);

    const days = daySchedules(weekTable([twoSlots, wednesday]));

    expect(days.map((day) => day.weekday)).toEqual([
      "mon",
      "tue",
      "wed",
      "thu",
      "fri",
    ]);
    expect(days[0].lessons).toEqual([
      { period: 1, time: FIRST, course: twoSlots },
      { period: 2, time: SECOND, course: twoSlots },
    ]);
    expect(days[1].lessons).toEqual([]);
    expect(days[2].lessons).toEqual([
      { period: 3, time: THIRD, course: wednesday },
    ]);
  });

  it("keeps two courses in the same slot in the order of the table", () => {
    const first = course("科目A", [{ weekday: "tue", period: 2 }]);
    const second = course("科目B", [{ weekday: "tue", period: 2 }]);

    const days = daySchedules(weekTable([first, second]));

    expect(days[1].lessons).toEqual([
      { period: 2, time: SECOND, course: first },
      { period: 2, time: SECOND, course: second },
    ]);
  });

  it("adds Saturday only when a course meets then", () => {
    const saturday = course("土曜の科目", [{ weekday: "sat", period: 7 }]);

    const days = daySchedules(weekTable([saturday]));

    expect(days.map((day) => day.weekday)).toEqual([
      "mon",
      "tue",
      "wed",
      "thu",
      "fri",
      "sat",
    ]);
    expect(days[5].lessons).toEqual([
      { period: 7, time: SEVENTH, course: saturday },
    ]);
  });

  it("leaves courses without slots out of the days", () => {
    const days = daySchedules(weekTable([course("集中講義", [])]));

    expect(days.flatMap((day) => day.lessons)).toEqual([]);
  });
});
