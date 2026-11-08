import { describe, expect, it } from "vitest";

import type { PlacedCourse } from "@/lib/api/client";
import { weekTable } from "@/lib/timetable";

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
