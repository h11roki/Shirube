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
    expect(policy).not.toContain("ws:");
  });

  it("lets the form submission continue to Google for the login", () => {
    expect(contentSecurityPolicy(false)).toContain(
      "form-action 'self' https://accounts.google.com",
    );
  });

  it("allows eval and the dev socket only while developing", () => {
    const policy = contentSecurityPolicy(true);

    expect(policy).toContain("'unsafe-eval'");
    expect(policy).toContain("connect-src 'self' ws:");
  });
});

describe("the security headers", () => {
  it("name each header once and include the policy", () => {
    const headers = securityHeaders(false);
    const keys = headers.map((header) => header.key);

    expect(new Set(keys).size).toBe(keys.length);
    expect(keys).toEqual([
      "Content-Security-Policy",
      "X-Content-Type-Options",
      "X-Frame-Options",
      "Referrer-Policy",
      "Permissions-Policy",
    ]);
    expect(headers[0].value).toBe(contentSecurityPolicy(false));
  });
});
