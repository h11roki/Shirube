import { decodeProtectedHeader, jwtVerify } from "jose";
import { describe, expect, it } from "vitest";

import {
  BACKEND_AUDIENCE,
  BACKEND_ISSUER,
  BACKEND_TOKEN_SECONDS,
  backendToken,
} from "@/lib/backend-token";

const SECRET = "s".repeat(64);
const NOW = new Date("2026-10-18T09:30:15.900Z");
const NOW_SECONDS = Math.floor(NOW.getTime() / 1000);

describe("backendToken", () => {
  it("signs the subject for the backend with HS256", async () => {
    const token = await backendToken("google-subject", SECRET, NOW);

    const { payload } = await jwtVerify(
      token,
      new TextEncoder().encode(SECRET),
      {
        issuer: BACKEND_ISSUER,
        audience: BACKEND_AUDIENCE,
        currentDate: NOW,
      },
    );
    expect(decodeProtectedHeader(token).alg).toBe("HS256");
    expect(payload.sub).toBe("google-subject");
  });

  it("issues at the current whole second and expires exactly the lifetime later", async () => {
    const token = await backendToken("google-subject", SECRET, NOW);

    const { payload } = await jwtVerify(
      token,
      new TextEncoder().encode(SECRET),
      { currentDate: NOW },
    );
    expect(payload.iat).toBe(NOW_SECONDS);
    expect(payload.exp).toBe(NOW_SECONDS + BACKEND_TOKEN_SECONDS);
  });

  it("cannot be verified with another secret", async () => {
    const token = await backendToken("google-subject", SECRET, NOW);

    await expect(
      jwtVerify(token, new TextEncoder().encode("x".repeat(64)), {
        currentDate: NOW,
      }),
    ).rejects.toThrow();
  });
});
