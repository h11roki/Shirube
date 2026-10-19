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
