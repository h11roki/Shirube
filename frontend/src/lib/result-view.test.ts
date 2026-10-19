import { describe, expect, it } from "vitest";

import {
  activeStation,
  readResultView,
  resultViewHref,
} from "@/lib/result-view";

describe("result view", () => {
  it("opens the route unless the query asks for the timetable", () => {
    expect(readResultView(new URLSearchParams())).toEqual({
      view: "route",
      semester: null,
    });
    expect(readResultView(new URLSearchParams("view=map"))).toEqual({
      view: "route",
      semester: null,
    });
    expect(
      readResultView(new URLSearchParams("view=timetable&semester=3-autumn")),
    ).toEqual({ view: "timetable", semester: "3-autumn" });
  });

  it("links the route to the bare path and the timetable to its semester", () => {
    expect(resultViewHref("/plans/1", "route", "3-autumn")).toBe("/plans/1");
    expect(resultViewHref("/plans/1", "timetable")).toBe(
      "/plans/1?view=timetable",
    );
    expect(resultViewHref("/plans/1", "timetable", "3-autumn")).toBe(
      "/plans/1?view=timetable&semester=3-autumn",
    );
  });

  it("reads back what it links to", () => {
    const href = resultViewHref("/plans/1", "timetable", "4-spring");
    expect(readResultView(new URL(href, "http://x").searchParams)).toEqual({
      view: "timetable",
      semester: "4-spring",
    });
  });

  it("marks the last station that crossed the upper part of the screen", () => {
    expect(activeStation([100, 300, 900], 1000, false)).toBe(1);
    expect(activeStation([600, 900, 1200], 1000, false)).toBe(0);
    expect(activeStation([-800, -300, 200], 1000, true)).toBe(2);
  });
});
