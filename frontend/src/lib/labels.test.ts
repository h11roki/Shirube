import { describe, expect, it } from "vitest";

import type { PlacedCourse } from "@/lib/api/client";
import {
  classLabel,
  placementLabel,
  roleLabel,
  semesterLabel,
  slotsLabel,
} from "@/lib/labels";

function withSlots(slots: PlacedCourse["slots"]): PlacedCourse {
  return {
    name: "科目A",
    relevance: "core",
    reason: "理由",
    prerequisite_for: null,
    syllabus_code: "10000",
    section_code: "10000",
    class_code: null,
    slots,
    credits: 2,
    class_confirmed: true,
  };
}

describe("labels", () => {
  it("writes slots as weekday and period joined by a dot, or says there are none", () => {
    expect(
      slotsLabel(
        withSlots([
          { weekday: "mon", period: 1 },
          { weekday: "thu", period: 3 },
        ]),
      ),
    ).toBe("月1・木3");
    expect(slotsLabel(withSlots([]))).toBe("コマなし");
  });

  it("names a semester by grade and term", () => {
    expect(semesterLabel(3, "autumn")).toBe("3 回生 秋学期");
  });

  it("calls a core course a pillar and a foundation the base of the course it leads to", () => {
    expect(roleLabel({ relevance: "core", prerequisite_for: null })).toBe("柱");
    expect(
      roleLabel({ relevance: "foundation", prerequisite_for: "確率統計" }),
    ).toBe("確率統計の礎");
    expect(roleLabel({ relevance: "foundation", prerequisite_for: null })).toBe(
      "礎",
    );
  });

  it("writes where a placed course sits, its class, and its credits", () => {
    expect(
      placementLabel({
        ...withSlots([{ weekday: "mon", period: 4 }]),
        class_code: "6B",
      }),
    ).toBe("月4 ・ クラス 6B ・ 2 単位");
    expect(placementLabel(withSlots([]))).toBe("コマなし ・ 2 単位");
  });

  it("names a class without a code", () => {
    expect(classLabel("")).toBe("記号なし");
    expect(classLabel("TA")).toBe("TA");
  });
});
