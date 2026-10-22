import { describe, expect, it } from "vitest";

import { securityHeaders } from "@/lib/security-headers";

function policyOf(development: boolean): string {
  return (
    securityHeaders(development).find(
      (header) => header.key === "Content-Security-Policy",
    )?.value ?? ""
  );
}

describe("the content security policy", () => {
  it("keeps the site out of frames and its scripts and connections on its own origin", () => {
    const policy = policyOf(false);

    expect(policy).toContain("default-src 'self'");
    expect(policy).toContain("script-src 'self' 'unsafe-inline'");
    expect(policy).toContain("connect-src 'self'");
    expect(policy).toContain("frame-ancestors 'none'");
    expect(policy).toContain("object-src 'none'");
    expect(policy).toContain("base-uri 'self'");
    expect(policy).not.toContain("unsafe-eval");
  });

  it("allows eval only while developing", () => {
    expect(policyOf(true)).toContain("'unsafe-eval'");
  });
});

describe("the security headers", () => {
  it("carry the policy and the four other headers", () => {
    expect(securityHeaders(false).map((header) => header.key)).toEqual([
      "Content-Security-Policy",
      "X-Content-Type-Options",
      "X-Frame-Options",
      "Referrer-Policy",
      "Permissions-Policy",
    ]);
  });
});
