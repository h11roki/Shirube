import { describe, expect, it } from "vitest";

import type { OfferedCourses } from "@/lib/api/client";
import { chosenCourses, matchingCourses } from "@/lib/fixed-courses";

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
    expect(names(matchingCourses(OFFERED.courses, "回路 ii"))).toEqual([
      "電子回路Ⅱ",
    ]);
  });

  it("finds nothing when a word matches no course", () => {
    expect(matchingCourses(OFFERED.courses, "回路 英語")).toEqual([]);
  });
});
