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

function getRequest(headers: Record<string, string> = {}): Request {
  return new Request("http://frontend.test/api/plans/abc", { headers });
}

function postRequest(
  body: string,
  headers: Record<string, string> = {},
): Request {
  return new Request("http://frontend.test/api/plans", {
    method: "POST",
    body,
    headers: { "Content-Type": "application/json", ...headers },
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

  it.each(["cross-site", "same-site"])(
    "refuses a POST that the browser says came from %s without asking for the session",
    async (fetchSite) => {
      const fetchMock = backendReturns(new Response("{}", { status: 202 }));

      const response = await forwardToBackend(
        "/plans",
        postRequest("{}", { "Sec-Fetch-Site": fetchSite }),
      );

      expect(response.status).toBe(403);
      expect(await response.json()).toEqual({
        detail: "ほかのサイトからの要求は受け付けません",
      });
      expect(auth).not.toHaveBeenCalled();
      expect(fetchMock).not.toHaveBeenCalled();
    },
  );

  it.each<Record<string, string>>([
    { Origin: "https://evil.test", Host: "frontend.test" },
    { Origin: "null", Host: "frontend.test" },
    {
      Origin: "https://frontend:3000",
      Host: "frontend:3000",
      "X-Forwarded-Host": "shirube.example",
    },
  ])(
    "refuses a POST without Sec-Fetch-Site whose Origin is not this site: %o",
    async (headers) => {
      const fetchMock = backendReturns(new Response("{}", { status: 202 }));

      const response = await forwardToBackend(
        "/plans",
        postRequest("{}", headers),
      );

      expect(response.status).toBe(403);
      expect(fetchMock).not.toHaveBeenCalled();
    },
  );

  it.each<Record<string, string>>([
    { "Sec-Fetch-Site": "same-origin" },
    { "Sec-Fetch-Site": "none" },
    { Origin: "http://frontend.test", Host: "frontend.test" },
    {
      Origin: "https://shirube.example",
      Host: "frontend:3000",
      "X-Forwarded-Host": "Shirube.Example",
    },
    {
      Origin: "https://shirube.example",
      Host: "shirube.example",
      "X-Forwarded-Host": "",
    },
    {
      Origin: "https://shirube.example",
      Host: "frontend:3000",
      "X-Forwarded-Host": "shirube.example:443",
    },
    {},
  ])(
    "forwards a POST from this site or not from a browser: %o",
    async (headers) => {
      auth.mockResolvedValue(loggedInAs("google-subject"));
      const fetchMock = backendReturns(new Response("{}", { status: 202 }));

      const response = await forwardToBackend(
        "/plans",
        postRequest("{}", headers),
      );

      expect(response.status).toBe(202);
      expect(fetchMock).toHaveBeenCalledOnce();
    },
  );

  it("forwards a GET whatever site it came from", async () => {
    auth.mockResolvedValue(loggedInAs("google-subject"));
    const fetchMock = backendReturns(new Response("{}", { status: 200 }));

    const response = await forwardToBackend(
      "/plans",
      getRequest({ "Sec-Fetch-Site": "cross-site" }),
    );

    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it("refuses a body declared over 64KB and stops its upload", async () => {
    auth.mockResolvedValue(loggedInAs("google-subject"));
    const fetchMock = backendReturns(new Response("{}", { status: 202 }));
    const request = new Request("http://frontend.test/api/plans", {
      method: "POST",
      body: "{}",
      headers: { "Content-Length": String(64 * 1024 + 1) },
    });

    const response = await forwardToBackend("/plans", request);

    expect(response.status).toBe(413);
    expect(await response.json()).toEqual({
      detail: "要求の本文が大きすぎます",
    });
    expect(request.body?.locked).toBe(false);
    expect(request.bodyUsed).toBe(true);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("stops pulling a streamed body once it goes over 64KB", async () => {
    auth.mockResolvedValue(loggedInAs("google-subject"));
    const fetchMock = backendReturns(new Response("{}", { status: 202 }));
    let pulled = 0;
    const kilobytes = new ReadableStream<Uint8Array>({
      pull(controller) {
        pulled += 1;
        controller.enqueue(new Uint8Array(1024));
      },
    });
    const request = new Request("http://frontend.test/api/plans", {
      method: "POST",
      body: kilobytes,
      duplex: "half",
    } as RequestInit);

    const response = await forwardToBackend("/plans", request);

    expect(response.status).toBe(413);
    expect(pulled).toBeLessThan(70);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("refuses a body over 64KB and forwards one at the limit", async () => {
    auth.mockResolvedValue(loggedInAs("google-subject"));
    const fetchMock = backendReturns(new Response("{}", { status: 202 }));
    const atLimit = "x".repeat(64 * 1024);

    const refused = await forwardToBackend(
      "/plans",
      postRequest(`${atLimit}x`),
    );
    const forwarded = await forwardToBackend("/plans", postRequest(atLimit));

    expect(refused.status).toBe(413);
    expect(forwarded.status).toBe(202);
    expect(fetchMock).toHaveBeenCalledOnce();
    expect(await (sentRequest(fetchMock).init.body as Blob).text()).toBe(
      atLimit,
    );
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

  it("passes when to retry a refused plan through", async () => {
    auth.mockResolvedValue(loggedInAs("google-subject"));
    backendReturns(
      Response.json(
        { detail: "道標を作れるのは 1 人 1 日 3 件までです" },
        { status: 429, headers: { "Retry-After": "21600" } },
      ),
    );

    const response = await forwardToBackend("/plans", postRequest("{}"));

    expect(response.status).toBe(429);
    expect(response.headers.get("Retry-After")).toBe("21600");
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

  it("answers 504 instead of 502 when the backend does not answer in time", async () => {
    auth.mockResolvedValue(loggedInAs("google-subject"));
    vi.stubGlobal(
      "fetch",
      vi
        .fn<typeof fetch>()
        .mockRejectedValue(new DOMException("timed out", "TimeoutError")),
    );
    vi.spyOn(console, "error").mockImplementation(() => {});

    const response = await forwardToBackend("/plans", postRequest("{}"));

    expect(response.status).toBe(504);
    expect(await response.json()).toEqual({
      detail: "道標のサーバーが時間内に返りませんでした",
    });
  });

  it("answers 504 instead of a cut-off body when time runs out while reading the answer", async () => {
    auth.mockResolvedValue(loggedInAs("google-subject"));
    const stalledBody = new ReadableStream({
      start(controller) {
        controller.error(new DOMException("timed out", "TimeoutError"));
      },
    });
    backendReturns(new Response(stalledBody, { status: 201 }));
    vi.spyOn(console, "error").mockImplementation(() => {});

    const response = await forwardToBackend("/plans", postRequest("{}"));

    expect(response.status).toBe(504);
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
