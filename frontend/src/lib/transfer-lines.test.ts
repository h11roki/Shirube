import { describe, expect, it } from "vitest";

import { type Box, roundedPath, transferRoute } from "@/lib/transfer-lines";

const ticket = (left: number, top: number): Box => ({
  left,
  top,
  right: left + 300,
  bottom: top + 160,
});

describe("transferRoute", () => {
  it("runs along the gutter left of the column when both tickets share it", () => {
    expect(transferRoute(ticket(48, 0), ticket(48, 400))).toEqual([
      { x: 48, y: 80 },
      { x: 42, y: 80 },
      { x: 42, y: 480 },
      { x: 48, y: 480 },
    ]);
  });

  it("leaves a ticket below it, follows the gap between rows, and enters the other column from its gutter", () => {
    expect(transferRoute(ticket(48, 0), ticket(360, 400))).toEqual([
      { x: 198, y: 160 },
      { x: 198, y: 166 },
      { x: 354, y: 166 },
      { x: 354, y: 480 },
      { x: 360, y: 480 },
    ]);
  });

  it("leaves a ticket above it when the other one is in an earlier row", () => {
    expect(transferRoute(ticket(360, 400), ticket(48, 0))).toEqual([
      { x: 510, y: 400 },
      { x: 510, y: 394 },
      { x: 42, y: 394 },
      { x: 42, y: 80 },
      { x: 48, y: 80 },
    ]);
  });

  it("dips under the row when both tickets are in the same row", () => {
    expect(
      transferRoute(ticket(48, 0), { ...ticket(672, 0), bottom: 180 }),
    ).toEqual([
      { x: 198, y: 160 },
      { x: 198, y: 186 },
      { x: 822, y: 186 },
      { x: 822, y: 180 },
    ]);
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
