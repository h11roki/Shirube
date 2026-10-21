import { auth } from "@/auth";
import { backendToken } from "@/lib/backend-token";

const LOGIN_REQUIRED = { detail: "ログインしてください" };
const BACKEND_UNREACHABLE = { detail: "道標のサーバーに届きませんでした" };
const BACKEND_TIMED_OUT = {
  detail: "道標のサーバーが時間内に返りませんでした",
};
const CROSS_SITE = { detail: "ほかのサイトからの要求は受け付けません" };
const TOO_LARGE = { detail: "要求の本文が大きすぎます" };
const BACKEND_TIMEOUT_MS = 290_000;
const MAX_BODY_BYTES = 64 * 1024;
const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);
const TRUSTED_FETCH_SITES = new Set(["same-origin", "none"]);
const PASSED_HEADERS = ["Content-Type", "Retry-After"];
const BACKEND_PREFIX = "/api/v1";
const FRONTEND_PREFIX = "/api";

class BodyTooLargeError extends Error {}

function isCrossSite(request: Request): boolean {
  if (SAFE_METHODS.has(request.method)) {
    return false;
  }
  const fetchSite = request.headers.get("Sec-Fetch-Site");
  if (fetchSite !== null) {
    return !TRUSTED_FETCH_SITES.has(fetchSite);
  }
  const origin = request.headers.get("Origin");
  if (origin === null) {
    return false;
  }
  const host =
    request.headers.get("X-Forwarded-Host")?.split(",")[0].trim() ??
    request.headers.get("Host") ??
    new URL(request.url).host;
  return !URL.canParse(origin) || new URL(origin).host !== host;
}

async function readLimitedBody(
  request: Request,
): Promise<ArrayBuffer | undefined> {
  if (!request.body) {
    return undefined;
  }
  if (Number(request.headers.get("Content-Length")) > MAX_BODY_BYTES) {
    await request.body.cancel();
    throw new BodyTooLargeError();
  }
  const reader = request.body.getReader();
  const chunks: Uint8Array<ArrayBuffer>[] = [];
  let size = 0;
  for (let read = await reader.read(); !read.done; read = await reader.read()) {
    size += read.value.byteLength;
    if (size > MAX_BODY_BYTES) {
      await reader.cancel();
      throw new BodyTooLargeError();
    }
    chunks.push(read.value);
  }
  return new Blob(chunks).arrayBuffer();
}

function requiredEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`環境変数 ${name} が設定されていません`);
  }
  return value;
}

export async function forwardToBackend(
  path: string,
  incoming: Request,
): Promise<Response> {
  if (isCrossSite(incoming)) {
    return Response.json(CROSS_SITE, { status: 403 });
  }
  const session = await auth();
  if (!session?.googleSubject) {
    return Response.json(LOGIN_REQUIRED, { status: 401 });
  }
  const token = await backendToken(
    session.googleSubject,
    requiredEnv("AUTH_JWT_SECRET"),
    new Date(),
  );
  const url = `${requiredEnv("BACKEND_URL")}${BACKEND_PREFIX}${path}`;
  const headers = new Headers({ Authorization: `Bearer ${token}` });
  const requestType = incoming.headers.get("Content-Type");
  if (requestType) {
    headers.set("Content-Type", requestType);
  }
  let body: ArrayBuffer | undefined;
  try {
    body = await readLimitedBody(incoming);
  } catch (error) {
    if (error instanceof BodyTooLargeError) {
      return Response.json(TOO_LARGE, { status: 413 });
    }
    throw error;
  }
  let backend: Response;
  let backendBody: ArrayBuffer | null;
  try {
    backend = await fetch(url, {
      method: incoming.method,
      body,
      headers,
      cache: "no-store",
      redirect: "manual",
      signal: AbortSignal.timeout(BACKEND_TIMEOUT_MS),
    });
    backendBody = backend.body ? await backend.arrayBuffer() : null;
  } catch (error) {
    console.error("バックエンドへの転送に失敗しました", error);
    if (error instanceof DOMException && error.name === "TimeoutError") {
      return Response.json(BACKEND_TIMED_OUT, { status: 504 });
    }
    return Response.json(BACKEND_UNREACHABLE, { status: 502 });
  }
  const forwarded = new Headers();
  for (const name of PASSED_HEADERS) {
    const value = backend.headers.get(name);
    if (value) {
      forwarded.set(name, value);
    }
  }
  const location = backend.headers.get("Location");
  if (location?.startsWith(`${BACKEND_PREFIX}/`)) {
    forwarded.set(
      "Location",
      `${FRONTEND_PREFIX}${location.slice(BACKEND_PREFIX.length)}`,
    );
  }
  return new Response(backendBody, {
    status: backend.status,
    headers: forwarded,
  });
}
