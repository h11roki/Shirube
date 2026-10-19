import { describe, expect, it } from "vitest";

import type {
  PlacedCourse,
  Relevance,
  SemesterPlan,
  Term,
} from "@/lib/api/client";
import {
  pickSemester,
  routeTotals,
  semesterCourses,
  linkedNames,
  semesterKey,
  transfers,
} from "@/lib/roadmap";

function placed(name: string, relevance: Relevance, credits = 2): PlacedCourse {
  return {
    name,
    relevance,
    reason: "理由",
    prerequisite_for: null,
    syllabus_code: name,
    section_code: name,
    class_code: null,
    slots: [],
    credits,
    class_confirmed: true,
  };
}

function semester(
  grade: number,
  term: Term,
  courses: PlacedCourse[],
  continuing: PlacedCourse[] = [],
): SemesterPlan {
  return {
    grade,
    term,
    credits: courses.reduce((sum, course) => sum + course.credits, 0),
    courses,
    continuing,
  };
}

describe("roadmap", () => {
  const yearLong = placed("通年の授業", "core", 4);
  const semesters = [
    semester(3, "spring", [yearLong, placed("礎の授業", "foundation")]),
    semester(3, "autumn", [placed("柱の授業", "core")], [yearLong]),
  ];

  it("keys a semester by grade and term", () => {
    expect(semesterKey({ grade: 3, term: "autumn" })).toBe("3-autumn");
  });

  it("picks the semester named in the query, or the first one", () => {
    expect(pickSemester(semesters, "3-autumn")).toBe(semesters[1]);
    expect(pickSemester(semesters, "9-spring")).toBe(semesters[0]);
    expect(pickSemester(semesters, null)).toBe(semesters[0]);
    expect(pickSemester([], null)).toBeUndefined();
  });

  it("lists a semester's own courses before those carried over from spring", () => {
    expect(semesterCourses(semesters[1]).map((course) => course.name)).toEqual([
      "柱の授業",
      "通年の授業",
    ]);
  });

  it("totals the route without counting a year-long course twice", () => {
    expect(routeTotals(semesters)).toEqual({
      credits: 8,
      core: 2,
      foundation: 1,
    });
  });

  it("transfers each foundation, before, with or after its pillar, to the pillar's station", () => {
    const pillar = placed("確率統計", "core");
    const early = {
      ...placed("基礎数学", "foundation"),
      prerequisite_for: "確率統計",
    };
    const late = {
      ...placed("情報処理", "foundation"),
      prerequisite_for: "確率統計",
    };
    const orphan = {
      ...placed("実験", "foundation"),
      prerequisite_for: "置けなかった柱",
    };
    const linkedPillar = {
      ...placed("機械学習", "core"),
      prerequisite_for: "確率統計",
    };
    const together = {
      ...placed("同時の礎", "foundation"),
      prerequisite_for: "確率統計",
    };
    const route = [
      semester(2, "autumn", [early]),
      semester(3, "spring", [pillar, together]),
      semester(3, "autumn", [late, orphan, linkedPillar]),
    ];

    const found = transfers(route);

    expect(found.get("基礎数学")).toEqual({
      pillar: "確率統計",
      pillarSection: "確率統計",
      station: 1,
      semester: route[1],
    });
    expect(
      ["基礎数学", "同時の礎", "情報処理"].map(
        (name) => found.get(name)?.station,
      ),
    ).toEqual([1, 1, 1]);
    expect(found.has("実験")).toBe(false);
    expect(found.has("確率統計")).toBe(false);
    expect(found.has("機械学習")).toBe(false);
  });

  it("links a foundation to its pillar and a pillar to all its foundations", () => {
    const pillar = placed("確率統計", "core");
    const early = {
      ...placed("基礎数学", "foundation"),
      prerequisite_for: "確率統計",
    };
    const late = {
      ...placed("情報処理", "foundation"),
      prerequisite_for: "確率統計",
    };
    const found = transfers([
      semester(3, "spring", [early, pillar]),
      semester(3, "autumn", [late]),
    ]);

    expect([...linkedNames(found, "基礎数学")]).toEqual(["確率統計"]);
    expect([...linkedNames(found, "確率統計")].sort()).toEqual(
      ["基礎数学", "情報処理"].sort(),
    );
    expect(linkedNames(found, null).size).toBe(0);
    expect(linkedNames(found, "関係のない授業").size).toBe(0);
  });
});
