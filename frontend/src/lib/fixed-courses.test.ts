import { describe, expect, it } from "vitest";

import type { OfferedCourses } from "@/lib/api/client";
import openapi from "@/lib/api/openapi.json";
import {
  MAX_FIXED_COURSES,
  chosenCourses,
  matchingCourses,
  toggledCourses,
} from "@/lib/fixed-courses";

const OFFERED: OfferedCourses = {
  term: "spring",
  courses: [
    {
      name: "英語 S1",
      credits: 1,
      semesters: [{ grade: 1, term: "spring" }],
    },
    {
      name: "電子回路Ⅰ",
      credits: 2,
      semesters: [{ grade: 2, term: "spring" }],
    },
    {
      name: "電子回路Ⅱ",
      credits: 2,
      semesters: [{ grade: 2, term: "autumn" }],
    },
    {
      name: "電子回路Ⅲ",
      credits: 2,
      semesters: [{ grade: 3, term: "spring" }],
    },
  ],
};

const names = (courses: { name: string }[]) =>
  courses.map((course) => course.name);

describe("chosenCourses", () => {
  it("keeps only the chosen courses offered for the current grade and term, in the list's order", () => {
    expect(
      names(chosenCourses(OFFERED, ["電子回路Ⅱ", "前の回生の授業", "英語 S1"])),
    ).toEqual(["英語 S1", "電子回路Ⅱ"]);
  });

  it("chooses nothing when the list could not be read", () => {
    expect(chosenCourses(undefined, ["英語 S1"])).toEqual([]);
  });
});

describe("toggledCourses", () => {
  const chosen = chosenCourses(OFFERED, ["英語 S1", "電子回路Ⅱ"]);

  it("adds a course that is not chosen and removes one that is", () => {
    expect(toggledCourses(chosen, "電子回路Ⅰ")).toEqual([
      "英語 S1",
      "電子回路Ⅱ",
      "電子回路Ⅰ",
    ]);
    expect(toggledCourses(chosen, "英語 S1")).toEqual(["電子回路Ⅱ"]);
  });

  it("forgets the names missing from the current list, so switching grades never piles up more than the limit", () => {
    const afterSwitch = chosenCourses(OFFERED, [
      "前の回生だけの授業",
      "電子回路Ⅰ",
    ]);
    expect(toggledCourses(afterSwitch, "電子回路Ⅱ")).toEqual([
      "電子回路Ⅰ",
      "電子回路Ⅱ",
    ]);
  });
});

describe("MAX_FIXED_COURSES", () => {
  it("is the limit the API accepts", () => {
    expect(
      openapi.components.schemas.PlanIn.properties.fixed_courses.maxItems,
    ).toBe(MAX_FIXED_COURSES);
  });
});

describe("matchingCourses", () => {
  it("shows every course when the filter is blank", () => {
    expect(names(matchingCourses(OFFERED.courses, "  "))).toEqual(
      names(OFFERED.courses),
    );
  });

  it("matches every word of the filter regardless of width and case", () => {
    expect(names(matchingCourses(OFFERED.courses, "ｓ１　英語"))).toEqual([
      "英語 S1",
    ]);
  });

  it("matches Roman numerals typed in ASCII as part of a name, so ii also finds Ⅲ", () => {
    expect(names(matchingCourses(OFFERED.courses, "回路 ii"))).toEqual([
      "電子回路Ⅱ",
      "電子回路Ⅲ",
    ]);
  });

  it("finds nothing when a word matches no course", () => {
    expect(matchingCourses(OFFERED.courses, "回路 英語")).toEqual([]);
  });
});
