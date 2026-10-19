import { describe, expect, it } from "vitest";

import { progressSteps } from "@/lib/progress";

function states(...args: Parameters<typeof progressSteps>) {
  return progressSteps(...args).map((step) => `${step.stage}:${step.state}`);
}

describe("progressSteps", () => {
  it("leaves every step ahead while the plan waits in line", () => {
    expect(states("pending", null)).toEqual([
      "analyzing:later",
      "searching:later",
      "selecting:later",
      "placing:later",
    ]);
  });

  it("marks the steps before the current stage as done", () => {
    expect(states("running", "selecting")).toEqual([
      "analyzing:done",
      "searching:done",
      "selecting:now",
      "placing:later",
    ]);
  });

  it("shows a running plan without a stage at the first step", () => {
    expect(states("running", null)).toEqual([
      "analyzing:now",
      "searching:later",
      "selecting:later",
      "placing:later",
    ]);
  });
});
