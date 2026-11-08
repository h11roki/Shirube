import { describe, expect, it } from "vitest";

import {
  OCCUPATION_REQUIRED,
  SAME_OCCUPATION_NOTE,
  assumptionLabel,
  readingLabel,
} from "@/lib/labels";
import { rebuildProblem, rebuildRequest } from "@/lib/plan-request";
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

describe("読み取りの知らせ", () => {
  it("解釈した職業として作っていることと、前提を出す", () => {
    expect(readingLabel("ITエンジニア")).toBe("ITエンジニアとして作っています");
    expect(assumptionLabel("広く読んだ")).toBe("前提: 広く読んだ");
  });
});
