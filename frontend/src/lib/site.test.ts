import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { CATCHPHRASE } from "@/lib/site";

const FRONTEND = new URL("../../", import.meta.url);

function read(path: string): string {
  return readFileSync(new URL(path, FRONTEND), "utf8");
}

describe("the catchphrase", () => {
  it("reads the same on the share card and in its alt text", () => {
    expect(read("brand/opengraph-image.html")).toContain(
      CATCHPHRASE.join("<br />"),
    );
    expect(read("src/app/opengraph-image.alt.txt")).toContain(
      CATCHPHRASE.join(""),
    );
  });
});
