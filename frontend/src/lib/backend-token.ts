import { SignJWT } from "jose";

export const BACKEND_ISSUER = "shirube-frontend";
export const BACKEND_AUDIENCE = "shirube-backend";
export const BACKEND_TOKEN_SECONDS = 300;

export async function backendToken(
  subject: string,
  secret: string,
  now: Date,
): Promise<string> {
  const issuedAt = Math.floor(now.getTime() / 1000);
  return new SignJWT()
    .setProtectedHeader({ alg: "HS256" })
    .setSubject(subject)
    .setIssuer(BACKEND_ISSUER)
    .setAudience(BACKEND_AUDIENCE)
    .setIssuedAt(issuedAt)
    .setExpirationTime(issuedAt + BACKEND_TOKEN_SECONDS)
    .sign(new TextEncoder().encode(secret));
}
