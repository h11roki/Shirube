import { describe, expect, it } from "vitest";

import { contentSecurityPolicy, securityHeaders } from "@/lib/security-headers";

describe("the content security policy", () => {
  it("keeps the site out of frames and its scripts and connections on its own origin", () => {
    const policy = contentSecurityPolicy(false);

    expect(policy).toContain("default-src 'self'");
    expect(policy).toContain("script-src 'self' 'unsafe-inline'");
    expect(policy).toContain("connect-src 'self'");
    expect(policy).toContain("frame-ancestors 'none'");
    expect(policy).toContain("object-src 'none'");
    expect(policy).toContain("base-uri 'self'");
    expect(policy).not.toContain("unsafe-eval");
  });

  it("allows eval only while developing", () => {
    expect(contentSecurityPolicy(true)).toContain("'unsafe-eval'");
  });
});

describe("the security headers", () => {
  it("carry the policy and the four other headers", () => {
    const headers = securityHeaders(false);

    expect(headers.map((header) => header.key)).toEqual([
      "Content-Security-Policy",
      "X-Content-Type-Options",
      "X-Frame-Options",
      "Referrer-Policy",
      "Permissions-Policy",
    ]);
    expect(headers[0].value).toBe(contentSecurityPolicy(false));
  });
});
