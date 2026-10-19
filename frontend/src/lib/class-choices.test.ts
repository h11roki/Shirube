import { describe, expect, it } from "vitest";

import { offeredClasses } from "@/lib/class-choices";

const CHOICES = {
  term: "spring" as const,
  courses: [
    { name: "情報科学Ⅱ", class_codes: ["TA", "TB"] },
    { name: "記号なしと分かれた科目", class_codes: ["", "X"] },
  ],
};

describe("offeredClasses", () => {
  it("keeps only the classes offered for the current grade and term", () => {
    expect(
      offeredClasses(CHOICES, {
        情報科学Ⅱ: "TB",
        記号なしと分かれた科目: "",
        前の回生の科目: "TA",
        "情報科学Ⅱ ": "TZ",
      }),
    ).toEqual({ 情報科学Ⅱ: "TB", 記号なしと分かれた科目: "" });
  });

  it("sends no class when the choices could not be read", () => {
    expect(offeredClasses(undefined, { 情報科学Ⅱ: "TA" })).toEqual({});
  });
});
