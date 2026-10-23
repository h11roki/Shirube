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
    credits: 2,
    class_confirmed: true,
  };
}

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

  it("keeps courses without slots apart from the grid", () => {
    const intensive = course("集中講義", []);

    const table = weekTable([intensive]);

    expect(table.unscheduled).toEqual([intensive]);
    expect(table.rows.flatMap((row) => row.cells.flat())).toEqual([]);
  });
});

describe("daySchedules", () => {
  it("lists every weekday of the table with its lessons in period order", () => {
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
      { period: 1, course: twoSlots },
      { period: 2, course: twoSlots },
    ]);
    expect(days[1].lessons).toEqual([]);
    expect(days[2].lessons).toEqual([{ period: 3, course: wednesday }]);
  });

  it("keeps two courses in the same slot in the order of the table", () => {
    const first = course("科目A", [{ weekday: "tue", period: 2 }]);
    const second = course("科目B", [{ weekday: "tue", period: 2 }]);

    const days = daySchedules(weekTable([first, second]));

    expect(days[1].lessons).toEqual([
      { period: 2, course: first },
      { period: 2, course: second },
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
    expect(days[5].lessons).toEqual([{ period: 7, course: saturday }]);
  });

  it("leaves courses without slots out of the days", () => {
    const days = daySchedules(weekTable([course("集中講義", [])]));

    expect(days.flatMap((day) => day.lessons)).toEqual([]);
  });
});
