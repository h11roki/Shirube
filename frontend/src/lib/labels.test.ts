import { describe, expect, it } from "vitest";

import type { PlacedCourse } from "@/lib/api/client";
import {
  classLabel,
  roleLabel,
  semesterLabel,
  semesterReading,
  semesterShortLabel,
  slotsLabel,
  stationLabel,
  transferLabel,
  answeredLabel,
  routeEndLabel,
  failedAnswerLabel,
  forgetTakenLabel,
  markTakenLabel,
  unmarkTakenLabel,
  sourceNote,
  syllabusLinkLabel,
  deletePlanLabel,
  deletedPlanLabel,
  leaveSummary,
} from "@/lib/labels";

function withSlots(slots: PlacedCourse["slots"]): PlacedCourse {
  return {
    name: "科目A",
    relevance: "core",
    reason: "理由",
    prerequisite_for: null,
    syllabus_code: "10000",
    syllabus_url: null,
    section_code: "10000",
    class_code: null,
    slots,
    credits: 2,
    class_confirmed: true,
  };
}

describe("labels", () => {
  it("writes slots as weekday and period joined by a dot, or says there are none", () => {
    expect(
      slotsLabel(
        withSlots([
          { weekday: "mon", period: 1 },
          { weekday: "thu", period: 3 },
        ]),
      ),
    ).toBe("月1・木3");
    expect(slotsLabel(withSlots([]))).toBe("コマなし");
  });

  it("names a semester by grade and term", () => {
    expect(semesterLabel(3, "autumn")).toBe("3 回生 秋学期");
  });

  it("calls a core course a pillar and a foundation the base of the course it leads to", () => {
    expect(roleLabel({ relevance: "core", prerequisite_for: null })).toBe("柱");
    expect(
      roleLabel({ relevance: "foundation", prerequisite_for: "確率統計" }),
    ).toBe("確率統計の礎");
    expect(roleLabel({ relevance: "foundation", prerequisite_for: null })).toBe(
      "礎",
    );
  });

  it("reads a semester aloud and numbers its station", () => {
    expect(semesterReading(3, "spring")).toBe("さんかいせい はるがっき");
    expect(semesterShortLabel(3, "spring")).toBe("3回生 春");
    expect(semesterReading(4, "autumn")).toBe("よんかいせい あきがっき");
    expect(stationLabel(0)).toBe("SH01");
    expect(stationLabel(11)).toBe("SH12");
  });

  it("ends the route at the destination, or says it continues when cut short", () => {
    expect(routeEndLabel("組込みエンジニア", 4, 4)).toBe("組込みエンジニアへ");
    expect(routeEndLabel("組込みエンジニア", 2, 4)).toBe(
      "組込みエンジニアへ続きます",
    );
  });

  it("writes a transfer to the pillar's station", () => {
    expect(
      transferLabel({
        pillar: "確率統計",
        station: 0,
        semester: {
          grade: 3,
          term: "spring",
          credits: 2,
          courses: [],
          continuing: [],
        },
      }),
    ).toBe("乗換 → 確率統計(SH01 3 回生 春学期)");
  });

  it("tells what an answer about a taken course did and names its buttons", () => {
    expect(answeredLabel("情報処理", "mark")).toBe(
      "情報処理を外して置き直しました",
    );
    expect(answeredLabel("情報処理", "unmark")).toBe(
      "情報処理を戻して置き直しました",
    );
    expect(failedAnswerLabel("答えられません", null)).toBe("答えられません");
    expect(failedAnswerLabel("答えられません", "届きません")).toBe(
      "答えられません(道標も読み直せませんでした: 届きません)",
    );
    expect(markTakenLabel("情報処理")).toBe("情報処理はもう取った");
    expect(unmarkTakenLabel("情報処理")).toBe("情報処理を道標に戻す");
    expect(forgetTakenLabel("情報処理")).toBe("情報処理を取り消す");
  });

  it("names a class without a code", () => {
    expect(classLabel("")).toBe("記号なし");
    expect(classLabel("TA")).toBe("TA");
  });

  it("names the syllabus link and the source with the year of the timetable", () => {
    expect(syllabusLinkLabel("情報処理")).toBe(
      "情報処理のシラバスを新しいタブで開く",
    );
    expect(sourceNote(2026)).toBe(
      "授業の情報は、立命館大学の 2026 年度のシラバスと時間割表によります。来年度以降の学期も、2026 年度の時間割で組んでいます。",
    );
  });

  it("names what deleting and leaving remove", () => {
    expect(deletePlanLabel("組込みエンジニア")).toBe(
      "組込みエンジニアの道標を消す",
    );
    expect(deletedPlanLabel("組込みエンジニア")).toBe(
      "組込みエンジニアの道標を消しました",
    );
    expect(leaveSummary(55, 2)).toBe(
      "作った道標 55 件と、もう取ったと答えた授業 2 科目を全て消し、ログアウトします。",
    );
    expect(leaveSummary(0, undefined)).toBe(
      "作った道標 0 件と、もう取ったと答えた授業を全て消し、ログアウトします。",
    );
  });
});
