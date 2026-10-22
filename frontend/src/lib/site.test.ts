import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { CATCHPHRASE } from "@/lib/site";

const FRONTEND = new URL("../../", import.meta.url);

function read(path: string): string {
  return readFileSync(new URL(path, FRONTEND), "utf8");
}

const card = read("brand/opengraph-image.html");
const alt = read("src/app/opengraph-image.alt.txt");

describe("the share card", () => {
  it("shows the catchphrase, one part per line", () => {
    expect(card).toContain(CATCHPHRASE.join("<br />"));
  });

  it("reads the catchphrase and the line under it in the alt text", () => {
    const subtitle = /<p class="sub">\s*([^<]+?)\s*<\/p>/.exec(card)?.[1];

    expect(subtitle).toBeDefined();
    expect(alt).toContain(CATCHPHRASE.join(""));
    expect(alt).toContain(subtitle);
  });

  it("ends the alt text without a line break, which Next would copy into og:image:alt", () => {
    expect(alt).toBe(alt.trim());
  });
});
