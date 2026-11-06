import { describe, expect, it } from "vitest";

import type { PlacedCourse, Plan } from "@/lib/api/client";
import {
  classLabel,
  roleLabel,
  semesterLabel,
  semesterReading,
  semesterShortLabel,
  slotsLabel,
  stationLabel,
  answeredLabel,
  routeEndContinuation,
  failedAnswerLabel,
  forgetTakenLabel,
  markTakenLabel,
  unmarkTakenLabel,
  sourceNote,
  sampleLabel,
  syllabusLinkLabel,
  deletePlanLabel,
  deletedPlanLabel,
  leaveSummary,
  planTitlePrefix,
  completionNotice,
  stationsAway,
  hopPlace,
  backPlace,
  arrivalsLabel,
  classChoicesSummary,
  takenCoursesSummary,
  fixedCoursesSummary,
  offeredCourseNote,
  matchCountLabel,
  dropFixedLabel,
} from "@/lib/labels";
import { SAMPLE_PLAN } from "@/lib/sample-plan";

function inState(status: Plan["status"]): Plan {
  return { ...SAMPLE_PLAN, status, result: null };
}

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

  it("says the route continues only when it is cut short", () => {
    expect(routeEndContinuation(4, 4)).toBeNull();
    expect(routeEndContinuation(2, 4)).toBe("続きます");
  });

  it("says how far and which way the other end of a transfer is, in stations", () => {
    expect(stationsAway(0, 2)).toBe("↓ 2 駅先");
    expect(stationsAway(3, 1)).toBe("↑ 2 駅手前");
    expect(stationsAway(1, 1)).toBe("同じ駅");
  });

  it("names the way back to the ticket a transfer started from", () => {
    const hop = {
      name: "確率統計",
      station: 0,
      semester: {
        grade: 3,
        term: "spring" as const,
        credits: 2,
        courses: [],
        continuing: [],
      },
    };
    expect(hopPlace(hop)).toBe("SH01 3 回生 春学期");
    expect(backPlace(hop)).toBe("(SH01 3 回生 春学期)へ戻る");
    expect(arrivalsLabel(2)).toBe("乗り入れ 2 本");
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

  it("counts the courses in the folded sections of the form", () => {
    expect(classChoicesSummary(1)).toBe(
      "学科でクラスが分かれている科目(1 科目、任意)",
    );
    expect(takenCoursesSummary(2)).toBe("もう取ったと答えた授業(2 科目)");
  });

  it("describes the courses to place first", () => {
    expect(fixedCoursesSummary(2)).toBe("先に入れる授業(選んだ 2 科目、任意)");
    expect(
      offeredCourseNote({
        name: "電子回路Ⅰ",
        credits: 2,
        semesters: [
          { grade: 2, term: "spring" },
          { grade: 3, term: "spring" },
        ],
      }),
    ).toBe("2 単位 ・ 2回生 春、3回生 春");
    expect(matchCountLabel(12)).toBe("当てはまる授業 12 科目");
    expect(matchCountLabel(0)).toBe("当てはまる授業はありません");
    expect(dropFixedLabel("電子回路Ⅰ")).toBe("電子回路Ⅰを外す");
  });

  it("names a class without a code", () => {
    expect(classLabel("")).toBe("記号なし");
    expect(classLabel("TA")).toBe("TA");
  });

  it("names a sample plan by its occupation", () => {
    expect(sampleLabel("データサイエンティスト")).toBe(
      "見本 ── データサイエンティスト",
    );
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
    expect(leaveSummary(55, { count: 2 })).toBe(
      "作った道標 55 件と、もう取ったと答えた授業 2 科目を全て消し、ログアウトします。",
    );
    expect(leaveSummary(0, undefined)).toBe(
      "作った道標 0 件と、もう取ったと答えた授業を全て消し、ログアウトします。",
    );
    expect(leaveSummary(3, { failure: "サーバーに届きませんでした" })).toBe(
      "作った道標 3 件と、もう取ったと答えた授業を全て消し、ログアウトします。もう取ったと答えた授業の数は確かめられませんでした(サーバーに届きませんでした)。",
    );
  });

  it("puts the state of the plan in front of the tab title", () => {
    expect(planTitlePrefix(inState("pending"), false)).toBe("作成中: ");
    expect(planTitlePrefix(inState("running"), true)).toBe("作成中: ");
    expect(planTitlePrefix(SAMPLE_PLAN, true)).toBe("できました: ");
    expect(planTitlePrefix(inState("failed"), false)).toBe(
      "作れませんでした: ",
    );
  });

  it("adds nothing for a plan done before it was opened or done without a result", () => {
    expect(planTitlePrefix(SAMPLE_PLAN, false)).toBe("");
    expect(planTitlePrefix(inState("succeeded"), true)).toBe("");
  });

  it("announces completion only for a result that came after the plan was seen in progress", () => {
    expect(completionNotice(SAMPLE_PLAN, true)).toBe("道標ができました");
    expect(completionNotice(SAMPLE_PLAN, false)).toBe("");
    expect(completionNotice(inState("succeeded"), true)).toBe("");
    expect(completionNotice(inState("running"), true)).toBe("");
    expect(completionNotice(inState("failed"), true)).toBe("");
  });
});
