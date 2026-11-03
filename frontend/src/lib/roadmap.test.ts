import { describe, expect, it } from "vitest";

import type {
  PlacedCourse,
  Relevance,
  SemesterPlan,
  Term,
} from "@/lib/api/client";
import {
  courseNames,
  linkedNames,
  pickSemester,
  routeTotals,
  semesterCourses,
  semesterKey,
  ticketSerials,
  transferRoutes,
} from "@/lib/roadmap";

function placed(name: string, relevance: Relevance, credits = 2): PlacedCourse {
  return {
    name,
    relevance,
    reason: "理由",
    prerequisite_for: null,
    syllabus_code: name,
    syllabus_url: null,
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

  it("numbers the tickets in the order of the route, leaving out the courses continuing from the semester before", () => {
    expect([...ticketSerials(semesters)]).toEqual([
      ["通年の授業", "0001"],
      ["礎の授業", "0002"],
      ["柱の授業", "0003"],
    ]);
  });

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

  it("lists the name of every course in the plan once, carried over or left unplaced", () => {
    expect(
      courseNames({ semesters, unplaced: [placed("置けない授業", "core")] }),
    ).toEqual(["通年の授業", "礎の授業", "柱の授業", "置けない授業"]);
  });

  it("totals the route without counting a year-long course twice", () => {
    expect(routeTotals(semesters)).toEqual({
      credits: 8,
      core: 2,
      foundation: 1,
    });
  });

  describe("transfers", () => {
    const pillar = placed("確率統計", "core");
    const early = {
      ...placed("基礎数学", "foundation"),
      prerequisite_for: "確率統計",
    };
    const late = {
      ...placed("情報処理", "foundation"),
      prerequisite_for: "確率統計",
    };
    const together = {
      ...placed("同時の礎", "foundation"),
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
    const secondPillar = placed("信号処理", "core");
    const secondFoundation = {
      ...placed("回路理論", "foundation"),
      prerequisite_for: "信号処理",
    };
    const route = [
      semester(2, "autumn", [early, secondPillar]),
      semester(3, "spring", [pillar, together]),
      semester(3, "autumn", [late, orphan, linkedPillar, secondFoundation]),
    ];
    const routes = transferRoutes(route);

    it("transfers each foundation, before, with or after its pillar, to the pillar's first ticket", () => {
      expect(routes.departures.get("基礎数学")).toEqual({
        mark: "B",
        from: {
          name: "基礎数学",
          section: "基礎数学",
          station: 0,
          semester: route[0],
        },
        to: {
          name: "確率統計",
          section: "確率統計",
          station: 1,
          semester: route[1],
        },
      });
      expect(
        ["基礎数学", "同時の礎", "情報処理"].map((name) => {
          const transfer = routes.departures.get(name);
          return [transfer?.from.station, transfer?.to.station];
        }),
      ).toEqual([
        [0, 1],
        [1, 1],
        [2, 1],
      ]);
      expect(routes.departures.has("実験")).toBe(false);
      expect(routes.departures.has("確率統計")).toBe(false);
      expect(routes.departures.has("機械学習")).toBe(false);
    });

    it("marks each pillar with a letter in the order of the route", () => {
      expect(routes.departures.get("回路理論")?.mark).toBe("A");
      expect(
        [...routes.arrivals].map(([name, arrivals]) => [
          name,
          arrivals.map((transfer) => transfer.mark),
        ]),
      ).toEqual([
        ["信号処理", ["A"]],
        ["確率統計", ["B", "B", "B"]],
      ]);
    });

    it("marks the pillars after Z with two letters", () => {
      const many = transferRoutes([
        semester(
          3,
          "spring",
          Array.from({ length: 28 }, (_, index) => [
            placed(`柱${index}`, "core"),
            {
              ...placed(`礎${index}`, "foundation"),
              prerequisite_for: `柱${index}`,
            },
          ]).flat(),
        ),
      ]);
      expect(
        ["礎0", "礎25", "礎26", "礎27"].map(
          (name) => many.departures.get(name)?.mark,
        ),
      ).toEqual(["A", "Z", "AA", "AB"]);
    });

    it("lists a pillar's foundations in the order of the route", () => {
      expect(
        routes.arrivals.get("確率統計")?.map((transfer) => transfer.from.name),
      ).toEqual(["基礎数学", "同時の礎", "情報処理"]);
    });

    it("leads to the pillar's first ticket when the pillar comes again", () => {
      const again = transferRoutes([
        semester(3, "spring", [pillar, early]),
        semester(3, "autumn", [{ ...pillar, section_code: "後" }]),
      ]);
      expect(again.departures.get("基礎数学")?.to.section).toBe("確率統計");
    });

    it("links a foundation to its pillar and a pillar to all its foundations", () => {
      expect([...linkedNames(routes, "基礎数学")]).toEqual(["確率統計"]);
      expect([...linkedNames(routes, "確率統計")]).toEqual([
        "基礎数学",
        "同時の礎",
        "情報処理",
      ]);
      expect(linkedNames(routes, null).size).toBe(0);
      expect(linkedNames(routes, "関係のない授業").size).toBe(0);
    });
  });
});
