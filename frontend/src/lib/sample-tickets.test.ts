import { describe, expect, it } from "vitest";

import { SAMPLE_TICKETS, lastSentence } from "@/lib/sample-tickets";

describe("the sample tickets on the top page", () => {
  it("deal a foundation course and then a core course from the sample plan", () => {
    expect(SAMPLE_TICKETS.map((course) => course.relevance)).toEqual([
      "foundation",
      "core",
    ]);
  });

  it("show full-width letters in a course name at half width", () => {
    expect(SAMPLE_TICKETS.map((course) => course.name)).toEqual([
      "電子情報基礎数学",
      "AI・機械学習",
    ]);
  });

  it("are placed in a slot of the timetable", () => {
    for (const course of SAMPLE_TICKETS) {
      expect(course.slots).not.toHaveLength(0);
    }
  });
});

describe("the last sentence of a reason", () => {
  it("drops the sentences before it", () => {
    expect(
      lastSentence(
        "回帰と分類を MATLAB で実装するため。予測モデル開発に直結する。",
      ),
    ).toBe("予測モデル開発に直結する。");
  });

  it("keeps a single sentence whole", () => {
    expect(lastSentence("統計的判断の土台になる。")).toBe(
      "統計的判断の土台になる。",
    );
  });

  it("keeps the words after the last full stop", () => {
    expect(lastSentence("前提になるため。数学の道具")).toBe("数学の道具");
  });
});
