import { describe, expect, it } from "vitest";

import {
  SAMPLE_TICKETS,
  halfWidthAlphanumerics,
  lastSentence,
} from "@/lib/sample-tickets";

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

  it("quote the last sentence of each reason", () => {
    expect(SAMPLE_TICKETS.map((course) => course.reason)).toEqual([
      "確率分布や推定・検定で使う数学の前提になるため。",
      "予測モデル開発に直結する。",
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

  it("ends a sentence at an exclamation or question mark too", () => {
    expect(lastSentence("手を動かして学ぶ！現場の分析に役立つ。")).toBe(
      "現場の分析に役立つ。",
    );
  });

  it("keeps repeated marks at the end of one sentence", () => {
    expect(lastSentence("前提になるため。本当に役立つ！？")).toBe(
      "本当に役立つ！？",
    );
    expect(lastSentence("なぜ？？")).toBe("なぜ？？");
    expect(lastSentence("基礎になる。。")).toBe("基礎になる。。");
  });

  it("keeps a closing bracket or quote with the sentence it closes", () => {
    expect(lastSentence("先生は「基礎が要る。」と言う。だから取る。")).toBe(
      "だから取る。",
    );
    expect(lastSentence("基礎を固める。「分析の土台になる。」")).toBe(
      "「分析の土台になる。」",
    );
    expect(lastSentence("基礎を固める。“分析の土台になる。”")).toBe(
      "“分析の土台になる。”",
    );
  });

  it("keeps the words after the last full stop", () => {
    expect(lastSentence("前提になるため。数学の道具")).toBe("数学の道具");
  });

  it("leaves out the spaces around the sentence", () => {
    expect(lastSentence("前提になるため。 数学の道具になる。 ")).toBe(
      "数学の道具になる。",
    );
  });
});

describe("a course name shown at half width", () => {
  it("turns full-width letters and digits into half-width ones", () => {
    expect(halfWidthAlphanumerics("ＡＩ・機械学習２")).toBe("AI・機械学習2");
  });

  it("leaves Roman numerals, brackets, and other full-width marks as they are", () => {
    expect(halfWidthAlphanumerics("特殊講義（専門）Ⅲ～演習①")).toBe(
      "特殊講義（専門）Ⅲ～演習①",
    );
  });
});
