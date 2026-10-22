import { afterEach, describe, expect, it, vi } from "vitest";

import {
  hasSignedOut,
  requestJson,
  requestNothing,
  subscribeSignedOut,
} from "@/lib/api/client";

afterEach(() => {
  vi.unstubAllGlobals();
});

function refuseLogin() {
  vi.stubGlobal(
    "fetch",
    vi
      .fn<typeof fetch>()
      .mockResolvedValue(
        Response.json({ detail: "ログインしてください" }, { status: 401 }),
      ),
  );
}

describe("a refusal for a missing login", () => {
  it("marks the session as signed out, telling each listener once", async () => {
    const heard = vi.fn();
    const unsubscribe = subscribeSignedOut(heard);
    try {
      refuseLogin();
      await expect(requestJson("/api/plans")).rejects.toMatchObject({
        status: 401,
      });
      refuseLogin();
      await expect(requestNothing("/api/me")).rejects.toMatchObject({
        status: 401,
      });

      expect(hasSignedOut()).toBe(true);
      expect(heard).toHaveBeenCalledTimes(1);
    } finally {
      unsubscribe();
    }
  });
});
