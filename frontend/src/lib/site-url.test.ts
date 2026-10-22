import { afterEach, describe, expect, it, vi } from "vitest";

import { siteUrl } from "@/lib/site-url";

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("the site URL", () => {
  it("falls back to the local server when unset or empty", () => {
    vi.stubEnv("SITE_URL", undefined);
    expect(siteUrl().toString()).toBe("http://localhost:3000/");

    vi.stubEnv("SITE_URL", "");
    expect(siteUrl().toString()).toBe("http://localhost:3000/");
  });

  it("takes an origin from the environment", () => {
    vi.stubEnv("SITE_URL", "https://shirube.example");

    expect(siteUrl().origin).toBe("https://shirube.example");
  });

  it("refuses a value that is not a web URL or carries a path", () => {
    vi.stubEnv("SITE_URL", "shirube.example");
    expect(() => siteUrl()).toThrow(
      "SITE_URL を https://example.com のような URL に",
    );

    vi.stubEnv("SITE_URL", "localhost:3000");
    expect(() => siteUrl()).toThrow("http:// か https:// で始めてください");

    vi.stubEnv("SITE_URL", "ftp://shirube.example");
    expect(() => siteUrl()).toThrow("http:// か https:// で始めてください");

    vi.stubEnv("SITE_URL", "https://shirube.example/app");
    expect(() => siteUrl()).toThrow("パスを含めないでください");
  });
});
