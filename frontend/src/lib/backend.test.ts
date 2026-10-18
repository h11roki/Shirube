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

function getRequest(): Request {
  return new Request("http://frontend.test/api/plans/abc");
}

function postRequest(body: string): Request {
  return new Request("http://frontend.test/api/plans", {
    method: "POST",
    body,
    headers: { "Content-Type": "application/json" },
  });
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
  vi.restoreAllMocks();
  auth.mockReset();
});

describe("forwardToBackend", () => {
  it("asks to log in without reading the body or calling the backend when there is no session", async () => {
    auth.mockResolvedValue(null);
    const fetchMock = backendReturns(new Response(null, { status: 200 }));
    const request = postRequest("{}");

    const response = await forwardToBackend("/plans", request);

    expect(response.status).toBe(401);
    expect(await response.json()).toEqual({ detail: "ログインしてください" });
    expect(request.bodyUsed).toBe(false);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("asks to log in when the session has no Google subject", async () => {
    auth.mockResolvedValue({ expires: "2099-01-01T00:00:00.000Z" });
    const fetchMock = backendReturns(new Response(null, { status: 200 }));

    const response = await forwardToBackend("/plans/abc", getRequest());

    expect(response.status).toBe(401);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("sends the body and its content type with a token for the logged-in Google subject", async () => {
    auth.mockResolvedValue(loggedInAs("google-subject"));
    const fetchMock = backendReturns(new Response("{}", { status: 201 }));

    await forwardToBackend(
      "/plans",
      postRequest('{"occupation":"組込みエンジニア"}'),
    );

    const { url, init, headers } = sentRequest(fetchMock);
    expect(url).toBe(`${BACKEND_URL}/api/v1/plans`);
    expect(init.method).toBe("POST");
    expect(await new Response(init.body).text()).toBe(
      '{"occupation":"組込みエンジニア"}',
    );
    expect(headers.get("Content-Type")).toBe("application/json");
    const token = headers.get("Authorization")?.replace(/^Bearer /, "") ?? "";
    const { payload } = await jwtVerify(
      token,
      new TextEncoder().encode(SECRET),
      { issuer: BACKEND_ISSUER, audience: BACKEND_AUDIENCE },
    );
    expect(payload.sub).toBe("google-subject");
  });

  it("sends a GET without a body or content type", async () => {
    auth.mockResolvedValue(loggedInAs("google-subject"));
    const fetchMock = backendReturns(new Response("{}", { status: 200 }));

    await forwardToBackend("/plans/abc", getRequest());

    const { url, init, headers } = sentRequest(fetchMock);
    expect(url).toBe(`${BACKEND_URL}/api/v1/plans/abc`);
    expect(init.method).toBe("GET");
    expect(init.body).toBeUndefined();
    expect(headers.has("Content-Type")).toBe(false);
  });

  it("leaves redirects to the browser instead of following them with the token", async () => {
    auth.mockResolvedValue(loggedInAs("google-subject"));
    const fetchMock = backendReturns(new Response("{}", { status: 200 }));

    await forwardToBackend("/plans/abc", getRequest());

    expect(sentRequest(fetchMock).init.redirect).toBe("manual");
  });

  it("passes the backend status, body and content type through", async () => {
    auth.mockResolvedValue(loggedInAs("google-subject"));
    backendReturns(
      Response.json({ detail: "道標が見つかりません" }, { status: 404 }),
    );

    const response = await forwardToBackend("/plans/abc", getRequest());

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

    const response = await forwardToBackend("/plans", postRequest("{}"));

    expect(response.headers.get("Location")).toBe("/api/plans/abc");
  });

  it.each(["http://elsewhere.test/", "/api/v10/plans/abc"])(
    "drops a Location outside the backend API: %s",
    async (location) => {
      auth.mockResolvedValue(loggedInAs("google-subject"));
      backendReturns(
        new Response("{}", { status: 201, headers: { Location: location } }),
      );

      const response = await forwardToBackend("/plans", postRequest("{}"));

      expect(response.headers.has("Location")).toBe(false);
    },
  );

  it("answers 502 and logs the cause when the backend cannot be reached", async () => {
    auth.mockResolvedValue(loggedInAs("google-subject"));
    const cause = new TypeError("fetch failed");
    vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockRejectedValue(cause));
    const logError = vi.spyOn(console, "error").mockImplementation(() => {});

    const response = await forwardToBackend("/plans/abc", getRequest());

    expect(response.status).toBe(502);
    expect(await response.json()).toEqual({
      detail: "道標のサーバーに届きませんでした",
    });
    expect(logError).toHaveBeenCalledWith(expect.any(String), cause);
  });

  it.each(["AUTH_JWT_SECRET", "BACKEND_URL"])(
    "fails loudly without calling the backend when %s is not configured",
    async (name) => {
      auth.mockResolvedValue(loggedInAs("google-subject"));
      vi.stubEnv(name, "");
      const fetchMock = backendReturns(new Response(null, { status: 200 }));

      await expect(
        forwardToBackend("/plans/abc", getRequest()),
      ).rejects.toThrow(name);
      expect(fetchMock).not.toHaveBeenCalled();
    },
  );
});
