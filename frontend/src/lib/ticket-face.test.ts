import { describe, expect, it } from "vitest";

import { stampTilt } from "@/lib/ticket-face";

describe("ticket face", () => {
  it("tilts a stamp the same way every time for the same course", () => {
    expect(stampTilt("確率統計")).toBe(stampTilt("確率統計"));
  });

  it("tilts stamps a little to the left, between 4 and 10 degrees", () => {
    for (const name of [
      "確率統計",
      "電子情報基礎数学",
      "情報処理",
      "ＡＩ・機械学習",
    ]) {
      expect(stampTilt(name)).toBeGreaterThanOrEqual(-10);
      expect(stampTilt(name)).toBeLessThanOrEqual(-4);
    }
  });

  it("varies the tilt between courses", () => {
    const tilts = new Set(
      [
        "確率統計",
        "電子情報基礎数学",
        "情報処理",
        "ＡＩ・機械学習",
        "データ構造とアルゴリズム",
        "メディア情報処理",
      ].map(stampTilt),
    );
    expect(tilts.size).toBeGreaterThan(1);
  });
});
