import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { slotsLabel } from "@/lib/labels";
import { SAMPLE_TICKETS } from "@/lib/sample-tickets";
import { CATCHPHRASE, SUBHEAD } from "@/lib/site";

const FRONTEND = new URL("../../", import.meta.url);

function read(path: string): string {
  return readFileSync(new URL(path, FRONTEND), "utf8");
}

function field(ticket: string, pattern: RegExp): string | undefined {
  return pattern.exec(ticket)?.[1]?.trim();
}

const card = read("brand/opengraph-image.html");
const alt = read("src/app/opengraph-image.alt.txt");
const tickets = [
  ...card.matchAll(/<article class="ticket [^"]*">([\s\S]*?)<\/article>/g),
].map(([, ticket]) => ({
  name: field(ticket, /<p class="name">([^<]+)<\/p>/),
  reason: field(ticket, /<p class="reason">([^<]+)<\/p>/),
  slots: field(ticket, /<dt>コマ<\/dt>\s*<dd>([^<]+)<\/dd>/),
  credits: field(ticket, /<dt>単位<\/dt>\s*<dd>([^<]+)<\/dd>/),
}));

describe("the share card", () => {
  it("shows the catchphrase, one part per line, and the subhead", () => {
    expect(card).toContain(CATCHPHRASE.join("<br />"));
    expect(card).toContain(SUBHEAD);
  });

  it("reads the catchphrase and then the subhead in the alt text", () => {
    expect(alt).toContain(CATCHPHRASE.join("") + SUBHEAD);
  });

  it("shows the same tickets as the top page", () => {
    expect(tickets).toEqual(
      SAMPLE_TICKETS.map((course) => ({
        name: course.name,
        reason: course.reason,
        slots: slotsLabel(course),
        credits: String(course.credits),
      })),
    );
  });

  it("names the courses on its tickets and the reason of the core one in the alt text", () => {
    expect(tickets).not.toHaveLength(0);
    for (const course of SAMPLE_TICKETS) {
      expect(alt).toContain(course.name);
    }
    for (const course of SAMPLE_TICKETS.filter(
      (ticket) => ticket.relevance === "core",
    )) {
      expect(alt).toContain(course.reason);
    }
  });

  it("ends the alt text without a line break, which Next would copy into og:image:alt", () => {
    expect(alt).toBe(alt.trim());
  });
});
