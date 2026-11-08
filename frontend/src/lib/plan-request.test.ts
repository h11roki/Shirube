import { describe, expect, it } from "vitest";

import { OCCUPATION_REQUIRED, SAME_OCCUPATION_NOTE } from "@/lib/labels";
import {
  occupationProblem,
  rebuildProblem,
  rebuildRequest,
} from "@/lib/plan-request";
import { SAMPLE_PLAN } from "@/lib/sample-plan";

const CONDITIONS = {
  ...SAMPLE_PLAN.conditions,
  occupation: "Webエンジニア",
  grade: 2,
  term: "autumn" as const,
  chosen_classes: { 確率統計: "6B" },
  fixed_courses: ["電子回路Ⅰ"],
};

describe("別の職業名で作り直す", () => {
  it("職業名だけを替え、ほかの条件はこの道標のまま送る", () => {
    expect(rebuildRequest("  ソフトウェアエンジニア ", CONDITIONS)).toEqual({
      occupation: "ソフトウェアエンジニア",
      grade: 2,
      term: "autumn",
      department: "情",
      chosen_classes: { 確率統計: "6B" },
      fixed_courses: ["電子回路Ⅰ"],
    });
  });

  it("空の職業名と、前後の空白を除いてこの道標と同じ職業名は送らない", () => {
    expect(rebuildProblem(" 　", CONDITIONS)).toBe(OCCUPATION_REQUIRED);
    expect(rebuildProblem(" Webエンジニア ", CONDITIONS)).toBe(
      SAME_OCCUPATION_NOTE,
    );
    expect(rebuildProblem("ソフトウェアエンジニア", CONDITIONS)).toBeNull();
  });
});

describe("職業名", () => {
  it("空白だけなら入れるよう断り、何か書いてあれば通す", () => {
    expect(occupationProblem(" 　\n")).toBe(OCCUPATION_REQUIRED);
    expect(occupationProblem(" 職業 ")).toBeNull();
  });
});
