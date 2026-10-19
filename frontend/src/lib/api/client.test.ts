import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  isTemporary,
  messageOf,
  requestJson,
} from "@/lib/api/client";

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

  it("treats a successful answer that is not JSON as an error instead of returning nothing", async () => {
    respondWith(new Response("<html>", { status: 200 }));

    await expect(requestJson("/api/plans")).rejects.toMatchObject({
      status: 200,
      message: "道標のサーバーとやり取りできませんでした",
    });
  });
});

describe("errors", () => {
  it("are temporary when the network or the server failed, not when the request was wrong", () => {
    expect(isTemporary(new ApiError(0, "届かない"))).toBe(true);
    expect(isTemporary(new ApiError(502, "届かない"))).toBe(true);
    expect(isTemporary(new ApiError(404, "無い"))).toBe(false);
    expect(isTemporary(new TypeError("壊れた"))).toBe(false);
  });

  it("give their message, or the fixed sentence when they are not errors", () => {
    expect(messageOf(new ApiError(422, "直してください"))).toBe(
      "直してください",
    );
    expect(messageOf("文字列")).toBe(
      "道標のサーバーとやり取りできませんでした",
    );
  });
});
