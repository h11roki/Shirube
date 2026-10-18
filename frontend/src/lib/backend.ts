import { auth } from "@/auth";
import { backendToken } from "@/lib/backend-token";

const LOGIN_REQUIRED = { detail: "ログインしてください" };
const BACKEND_UNREACHABLE = { detail: "道標のサーバーに届きませんでした" };
const BACKEND_TIMED_OUT = {
  detail: "道標のサーバーが時間内に返りませんでした",
};
const BACKEND_TIMEOUT_MS = 290_000;
const BACKEND_PREFIX = "/api/v1";
const FRONTEND_PREFIX = "/api";

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
  const body = incoming.body ? await incoming.arrayBuffer() : undefined;
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
  const responseType = backend.headers.get("Content-Type");
  if (responseType) {
    forwarded.set("Content-Type", responseType);
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
