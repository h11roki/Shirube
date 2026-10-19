import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, requestJson } from "@/lib/api/client";

afterEach(() => {
  vi.unstubAllGlobals();
});

function respondWith(response: Response) {
  const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(response);
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("requestJson", () => {
  it("returns the body of a successful answer without caching it", async () => {
    const fetchMock = respondWith(Response.json({ plans: [] }));

    await expect(requestJson("/api/plans")).resolves.toEqual({ plans: [] });
    expect(fetchMock.mock.calls[0][1]?.cache).toBe("no-store");
  });

  it("turns an error answer into its detail sentence and status", async () => {
    respondWith(
      Response.json(
        { detail: "科目A: 選べるクラスは TA、TB です" },
        { status: 422 },
      ),
    );

    const error = await requestJson("/api/plans").catch((caught) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 422,
      message: "科目A: 選べるクラスは TA、TB です",
    });
  });

  it("uses a fixed sentence when the answer has no detail or no answer comes", async () => {
    respondWith(new Response("<html>", { status: 500 }));
    await expect(requestJson("/api/plans")).rejects.toMatchObject({
      status: 500,
      message: "道標のサーバーとやり取りできませんでした",
    });

    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockRejectedValue(new TypeError("fetch failed")),
    );
    await expect(requestJson("/api/plans")).rejects.toMatchObject({
      status: 0,
      message: "道標のサーバーとやり取りできませんでした",
    });
  });
});
