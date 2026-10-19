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
  semesterKey,
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
});
