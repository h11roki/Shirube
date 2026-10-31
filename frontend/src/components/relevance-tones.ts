import {
  STAMP_RING,
  TICKET_GROUND,
  TICKET_SEAL,
  TICKET_STAMP,
} from "@/components/styles";
import type { Relevance } from "@/lib/api/client";

export const RELEVANCE_TONES: Record<
  Relevance,
  {
    text: string;
    sticky: string;
    stamp: string;
    mark: string;
    ground: string;
  }
> = {
  core: {
    text: "text-pillar",
    sticky: "rotate-[0.4deg] bg-pillar-soft",
    stamp: TICKET_STAMP,
    mark: `${STAMP_RING} rounded-full border border-pillar bg-pillar-soft [--ring-gap:var(--paper)] [--ring:var(--pillar)]`,
    ground: `${TICKET_GROUND} [--ground:color-mix(in_srgb,var(--pillar)_7%,transparent)]`,
  },
  foundation: {
    text: "text-route",
    sticky: "rotate-[-0.4deg] bg-route-soft",
    stamp: TICKET_SEAL,
    mark: `${STAMP_RING} border border-route bg-route-soft [--ring-gap:var(--paper)] [--ring:var(--route)]`,
    ground: `${TICKET_GROUND} [--ground:color-mix(in_srgb,var(--route)_8%,transparent)]`,
  },
};

export const RELEVANCES = Object.keys(RELEVANCE_TONES) as Relevance[];
