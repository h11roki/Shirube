import { describe, expect, it } from "vitest";

import { POLL_LIMIT_MS, watchState } from "@/lib/polling";

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
