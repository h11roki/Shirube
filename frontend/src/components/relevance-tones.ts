import type { Relevance } from "@/lib/api/client";

export const RELEVANCE_TONES: Record<
  Relevance,
  { text: string; fill: string; sticky: string }
> = {
  core: {
    text: "text-pillar",
    fill: "bg-pillar",
    sticky: "rotate-[0.4deg] bg-pillar-soft",
  },
  foundation: {
    text: "text-route",
    fill: "bg-route",
    sticky: "rotate-[-0.4deg] bg-route-soft",
  },
};

export const RELEVANCES = Object.keys(RELEVANCE_TONES) as Relevance[];
