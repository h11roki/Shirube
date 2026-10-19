import { describe, expect, it } from "vitest";

import { POLL_LIMIT_MS, watchAfterFailure, watchState } from "@/lib/polling";

describe("watchState", () => {
  it("stops as soon as the plan has succeeded or failed", () => {
    expect(watchState("succeeded", 0)).toBe("finished");
    expect(watchState("failed", POLL_LIMIT_MS * 2)).toBe("finished");
  });

  it("keeps waiting for a waiting or running plan until the limit", () => {
    expect(watchState("pending", 0)).toBe("waiting");
    expect(watchState("running", POLL_LIMIT_MS - 1)).toBe("waiting");
  });

  it("gives up once the limit has passed", () => {
    expect(POLL_LIMIT_MS).toBe(180_000);
    expect(watchState("pending", POLL_LIMIT_MS)).toBe("gave-up");
    expect(watchState("running", POLL_LIMIT_MS + 1)).toBe("gave-up");
  });
});

describe("watchAfterFailure", () => {
  it("tries again after a temporary failure until the limit, then gives up", () => {
    expect(watchAfterFailure(true, 0)).toBe("waiting");
    expect(watchAfterFailure(true, POLL_LIMIT_MS)).toBe("gave-up");
  });

  it("fails at once when the failure will not pass", () => {
    expect(watchAfterFailure(false, 0)).toBe("failed");
  });
});
