import { jwtVerify } from "jose";
import type { Session } from "next-auth";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { BACKEND_AUDIENCE, BACKEND_ISSUER } from "@/lib/backend-token";
import { forwardToBackend } from "@/lib/backend";

const auth = vi.hoisted(() => vi.fn<() => Promise<Session | null>>());
vi.mock("@/auth", () => ({ auth }));

const SECRET = "s".repeat(64);
const BACKEND_URL = "http://backend.test";

function loggedInAs(googleSubject: string): Session {
  return {
    user: { name: "高橋" },
    expires: "2099-01-01T00:00:00.000Z",
    googleSubject,
  };
}

function backendReturns(response: Response) {
  const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(response);
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function sentRequest(fetchMock: ReturnType<typeof backendReturns>) {
  const [url, init] = fetchMock.mock.calls[0];
  return { url, init: init ?? {}, headers: new Headers(init?.headers) };
}

beforeEach(() => {
  vi.stubEnv("AUTH_JWT_SECRET", SECRET);
  vi.stubEnv("BACKEND_URL", BACKEND_URL);
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  auth.mockReset();
});

describe("forwardToBackend", () => {
  it("asks to log in without calling the backend when there is no session", async () => {
    auth.mockResolvedValue(null);
    const fetchMock = backendReturns(new Response(null, { status: 200 }));

    const response = await forwardToBackend("/plans", { method: "GET" });

    expect(response.status).toBe(401);
    expect(await response.json()).toEqual({ detail: "ログインしてください" });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("asks to log in when the session has no Google subject", async () => {
    auth.mockResolvedValue({ expires: "2099-01-01T00:00:00.000Z" });
    const fetchMock = backendReturns(new Response(null, { status: 200 }));

    const response = await forwardToBackend("/plans", { method: "GET" });

    expect(response.status).toBe(401);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("sends the request body with a token for the logged-in Google subject", async () => {
    auth.mockResolvedValue(loggedInAs("google-subject"));
    const fetchMock = backendReturns(new Response("{}", { status: 201 }));

    await forwardToBackend("/plans", {
      method: "POST",
      body: '{"occupation":"組込みエンジニア"}',
    });

    const { url, init, headers } = sentRequest(fetchMock);
    expect(url).toBe(`${BACKEND_URL}/api/v1/plans`);
    expect(init.method).toBe("POST");
    expect(init.body).toBe('{"occupation":"組込みエンジニア"}');
    expect(headers.get("Content-Type")).toBe("application/json");
    const token = headers.get("Authorization")?.replace(/^Bearer /, "") ?? "";
    const { payload } = await jwtVerify(
      token,
      new TextEncoder().encode(SECRET),
      { issuer: BACKEND_ISSUER, audience: BACKEND_AUDIENCE },
    );
    expect(payload.sub).toBe("google-subject");
  });

  it("sends a GET without a body", async () => {
    auth.mockResolvedValue(loggedInAs("google-subject"));
    const fetchMock = backendReturns(new Response("{}", { status: 200 }));

    await forwardToBackend("/plans/abc", { method: "GET" });

    const { url, init, headers } = sentRequest(fetchMock);
    expect(url).toBe(`${BACKEND_URL}/api/v1/plans/abc`);
    expect(init.method).toBe("GET");
    expect(init.body).toBeUndefined();
    expect(headers.has("Content-Type")).toBe(false);
  });

  it("passes the backend status, body and content type through", async () => {
    auth.mockResolvedValue(loggedInAs("google-subject"));
    backendReturns(
      Response.json({ detail: "道標が見つかりません" }, { status: 404 }),
    );

    const response = await forwardToBackend("/plans/abc", { method: "GET" });

    expect(response.status).toBe(404);
    expect(response.headers.get("Content-Type")).toBe("application/json");
    expect(await response.json()).toEqual({ detail: "道標が見つかりません" });
  });

  it("points the Location of a created plan at the frontend route", async () => {
    auth.mockResolvedValue(loggedInAs("google-subject"));
    backendReturns(
      new Response("{}", {
        status: 201,
        headers: { Location: "/api/v1/plans/abc" },
      }),
    );

    const response = await forwardToBackend("/plans", {
      method: "POST",
      body: "{}",
    });

    expect(response.headers.get("Location")).toBe("/api/plans/abc");
  });

  it("drops a Location outside the backend API", async () => {
    auth.mockResolvedValue(loggedInAs("google-subject"));
    backendReturns(
      new Response(null, {
        status: 307,
        headers: { Location: "http://elsewhere.test/" },
      }),
    );

    const response = await forwardToBackend("/plans", { method: "GET" });

    expect(response.headers.has("Location")).toBe(false);
  });

  it("answers 502 when the backend cannot be reached", async () => {
    auth.mockResolvedValue(loggedInAs("google-subject"));
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockRejectedValue(new TypeError("fetch failed")),
    );

    const response = await forwardToBackend("/plans", { method: "GET" });

    expect(response.status).toBe(502);
    expect(await response.json()).toEqual({
      detail: "道標のサーバーに届きませんでした",
    });
  });

  it("fails loudly when the signing secret is not configured", async () => {
    auth.mockResolvedValue(loggedInAs("google-subject"));
    vi.stubEnv("AUTH_JWT_SECRET", "");
    backendReturns(new Response(null, { status: 200 }));

    await expect(forwardToBackend("/plans", { method: "GET" })).rejects.toThrow(
      "AUTH_JWT_SECRET",
    );
  });
});
