import { describe, expect, it } from "vitest";

import {
  type Box,
  type Layout,
  offscreenSide,
  roundedPath,
  transferRoute,
} from "@/lib/transfer-lines";

const GAPS = { row: 12, column: 12 };
const SAME_GRID: Layout = { gaps: GAPS, gutter: 42, sameGrid: true };
const OTHER_GRID: Layout = { ...SAME_GRID, sameGrid: false };

const ticket = (left: number, top: number): Box => ({
  left,
  top,
  right: left + 300,
  bottom: top + 160,
});

describe("transferRoute", () => {
  it("runs along the gutter left of the column when both tickets share it in one semester", () => {
    expect(transferRoute(ticket(360, 0), ticket(360, 344), SAME_GRID)).toEqual([
      { x: 360, y: 80 },
      { x: 354, y: 80 },
      { x: 354, y: 424 },
      { x: 360, y: 424 },
    ]);
  });

  it("follows the gap between two neighbouring rows of one semester", () => {
    expect(transferRoute(ticket(48, 0), ticket(360, 172), SAME_GRID)).toEqual([
      { x: 198, y: 160 },
      { x: 198, y: 166 },
      { x: 510, y: 166 },
      { x: 510, y: 172 },
    ]);
  });

  it("goes round by the gutter left of the route to reach another semester, so it never crosses the stations between", () => {
    expect(transferRoute(ticket(48, 0), ticket(360, 600), OTHER_GRID)).toEqual([
      { x: 198, y: 160 },
      { x: 198, y: 166 },
      { x: 42, y: 166 },
      { x: 42, y: 594 },
      { x: 510, y: 594 },
      { x: 510, y: 600 },
    ]);
  });

  it("leaves a ticket from its top when the other one is in an earlier semester", () => {
    expect(transferRoute(ticket(360, 600), ticket(360, 0), OTHER_GRID)).toEqual(
      [
        { x: 510, y: 600 },
        { x: 510, y: 594 },
        { x: 42, y: 594 },
        { x: 42, y: 166 },
        { x: 510, y: 166 },
        { x: 510, y: 160 },
      ],
    );
  });

  it("keeps to the middle of wider gaps when the text is enlarged", () => {
    expect(
      transferRoute(ticket(96, 0), ticket(96, 400), {
        gaps: { row: 24, column: 24 },
        gutter: 84,
        sameGrid: true,
      }),
    ).toEqual([
      { x: 96, y: 80 },
      { x: 84, y: 80 },
      { x: 84, y: 480 },
      { x: 96, y: 480 },
    ]);
  });

  it("dips under the row when both tickets are in the same row", () => {
    expect(
      transferRoute(
        ticket(48, 0),
        { ...ticket(672, 0), bottom: 180 },
        SAME_GRID,
      ),
    ).toEqual([
      { x: 198, y: 160 },
      { x: 198, y: 186 },
      { x: 822, y: 186 },
      { x: 822, y: 180 },
    ]);
  });
});

describe("offscreenSide", () => {
  it("counts a ticket hidden under the strip at the top as above", () => {
    expect(offscreenSide({ top: 10, bottom: 60 }, 70, 800)).toBe("above");
  });

  it("counts a ticket past the bottom of the screen as below", () => {
    expect(offscreenSide({ top: 810, bottom: 970 }, 70, 800)).toBe("below");
  });

  it("leaves a ticket that can be seen even partly", () => {
    expect(offscreenSide({ top: 40, bottom: 200 }, 70, 800)).toBeNull();
    expect(offscreenSide({ top: 780, bottom: 940 }, 70, 800)).toBeNull();
  });
});

describe("roundedPath", () => {
  it("rounds each corner without overshooting short segments", () => {
    expect(
      roundedPath(
        [
          { x: 0, y: 0 },
          { x: 0, y: 6 },
          { x: 100, y: 6 },
        ],
        6,
      ),
    ).toBe("M 0 0 L 0 3 Q 0 6 3 6 L 100 6");
  });

  it("passes through a corner whose segment has no length instead of dividing by zero", () => {
    expect(
      roundedPath(
        [
          { x: 0, y: 0 },
          { x: 0, y: 6 },
          { x: 0, y: 6 },
          { x: 0, y: 40 },
        ],
        6,
      ),
    ).toBe("M 0 0 L 0 6 L 0 6 L 0 40");
  });

  it("draws a straight line when there is no corner", () => {
    expect(
      roundedPath(
        [
          { x: 0, y: 0 },
          { x: 10, y: 0 },
        ],
        6,
      ),
    ).toBe("M 0 0 L 10 0");
  });
});
