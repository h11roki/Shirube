import { auth } from "@/auth";
import { backendToken } from "@/lib/backend-token";

const LOGIN_REQUIRED = { detail: "ログインしてください" };
const BACKEND_UNREACHABLE = { detail: "道標のサーバーに届きませんでした" };
const BACKEND_TIMEOUT_MS = 120_000;
const BACKEND_PREFIX = "/api/v1";
const FRONTEND_PREFIX = "/api";

type BackendRequest = { method: "GET" } | { method: "POST"; body: string };

function requiredEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`環境変数 ${name} が設定されていません`);
  }
  return value;
}

export async function forwardToBackend(
  path: string,
  request: BackendRequest,
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
  const headers = new Headers({ Authorization: `Bearer ${token}` });
  if (request.method === "POST") {
    headers.set("Content-Type", "application/json");
  }
  let backend: Response;
  try {
    backend = await fetch(
      `${requiredEnv("BACKEND_URL")}${BACKEND_PREFIX}${path}`,
      {
        method: request.method,
        body: request.method === "POST" ? request.body : undefined,
        headers,
        cache: "no-store",
        signal: AbortSignal.timeout(BACKEND_TIMEOUT_MS),
      },
    );
  } catch {
    return Response.json(BACKEND_UNREACHABLE, { status: 502 });
  }
  const forwarded = new Headers();
  const contentType = backend.headers.get("Content-Type");
  if (contentType) {
    forwarded.set("Content-Type", contentType);
  }
  const location = backend.headers.get("Location");
  if (location?.startsWith(BACKEND_PREFIX)) {
    forwarded.set(
      "Location",
      `${FRONTEND_PREFIX}${location.slice(BACKEND_PREFIX.length)}`,
    );
  }
  return new Response(backend.body, {
    status: backend.status,
    headers: forwarded,
  });
}
