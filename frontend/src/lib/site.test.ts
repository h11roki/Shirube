import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { CATCHPHRASE, SUBHEAD } from "@/lib/site";

const FRONTEND = new URL("../../", import.meta.url);

function read(path: string): string {
  return readFileSync(new URL(path, FRONTEND), "utf8");
}

const card = read("brand/opengraph-image.html");
const alt = read("src/app/opengraph-image.alt.txt");

describe("the share card", () => {
  it("shows the catchphrase, one part per line, and the subhead", () => {
    expect(card).toContain(CATCHPHRASE.join("<br />"));
    expect(card).toContain(SUBHEAD);
  });

  it("reads the catchphrase and then the subhead in the alt text", () => {
    expect(alt).toContain(CATCHPHRASE.join("") + SUBHEAD);
  });

  it("ends the alt text without a line break, which Next would copy into og:image:alt", () => {
    expect(alt).toBe(alt.trim());
  });
});
