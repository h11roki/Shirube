import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  deletePlan,
  hasSignedOut,
  isTemporary,
  messageOf,
  requestJson,
  requestNothing,
  subscribeSignedOut,
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

  it("treats a body cut off by the time limit as a network failure", async () => {
    const controller = new AbortController();
    const stalled = new Response(
      new ReadableStream({
        start(stream) {
          controller.signal.addEventListener("abort", () =>
            stream.error(new DOMException("timed out", "TimeoutError")),
          );
        },
      }),
      { status: 200 },
    );
    respondWith(stalled);

    const answer = requestJson("/api/plans", { signal: controller.signal });
    controller.abort();

    await expect(answer).rejects.toMatchObject({ status: 0 });
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

  it("ask to log in again when the login has run out", () => {
    expect(messageOf(new ApiError(401, "ログインしてください"))).toBe(
      "ログインが切れました。ページを読み直してログインしてください",
    );
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

describe("requestNothing", () => {
  it("accepts an answer without a body", async () => {
    const fetchMock = respondWith(new Response(null, { status: 204 }));

    await expect(
      requestNothing("/api/me", { method: "DELETE" }),
    ).resolves.toBeUndefined();
    expect(fetchMock.mock.calls[0][1]).toMatchObject({
      method: "DELETE",
      cache: "no-store",
    });
  });

  it("turns a refusal into its detail sentence and status", async () => {
    respondWith(
      Response.json(
        { detail: "作っている途中の道標は、できてから消せます" },
        { status: 409 },
      ),
    );

    await expect(
      requestNothing("/api/plans/abc", { method: "DELETE" }),
    ).rejects.toMatchObject({
      status: 409,
      message: "作っている途中の道標は、できてから消せます",
    });
  });
});

describe("deletePlan", () => {
  it("treats a plan that is already gone as deleted", async () => {
    respondWith(
      Response.json({ detail: "Plan がありません: abc" }, { status: 404 }),
    );

    await expect(deletePlan("abc")).resolves.toBeUndefined();
  });

  it("passes on any other refusal", async () => {
    respondWith(
      Response.json(
        { detail: "作っている途中の道標は、できてから消せます" },
        { status: 409 },
      ),
    );

    await expect(deletePlan("abc")).rejects.toMatchObject({ status: 409 });
  });
});

describe("a refusal for a missing login", () => {
  it("marks the session as signed out, telling each listener once", async () => {
    const heard = vi.fn();
    subscribeSignedOut(heard);
    respondWith(
      Response.json({ detail: "ログインしてください" }, { status: 401 }),
    );

    await expect(requestJson("/api/plans")).rejects.toMatchObject({
      status: 401,
    });
    respondWith(
      Response.json({ detail: "ログインしてください" }, { status: 401 }),
    );
    await expect(requestNothing("/api/me")).rejects.toMatchObject({
      status: 401,
    });

    expect(hasSignedOut()).toBe(true);
    expect(heard).toHaveBeenCalledTimes(1);
  });
});
