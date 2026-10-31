import { TICKET_GROUND } from "@/components/styles";
import type { Relevance } from "@/lib/api/client";

const STAMP_RING =
  "shadow-[inset_0_0_0_1.5px_var(--ring-gap),inset_0_0_0_2.25px_var(--ring)]";
const STAMP_OUTLINES: Record<Relevance, string> = {
  core: `${STAMP_RING} rounded-full border-pillar [--ring:var(--pillar)]`,
  foundation: `${STAMP_RING} border-route [--ring:var(--route)]`,
};
const TICKET_STAMP =
  "absolute grid place-items-center border-[1.5px] bg-note font-serif font-extrabold [--ring-gap:var(--note)]";
const LEGEND_MARK = "border [--ring-gap:var(--paper)]";

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
    stamp: `${TICKET_STAMP} ${STAMP_OUTLINES.core} text-pillar`,
    mark: `${LEGEND_MARK} ${STAMP_OUTLINES.core} bg-pillar-soft`,
    ground: `${TICKET_GROUND} [--ground:color-mix(in_srgb,var(--pillar)_7%,transparent)]`,
  },
  foundation: {
    text: "text-route",
    sticky: "rotate-[-0.4deg] bg-route-soft",
    stamp: `${TICKET_STAMP} ${STAMP_OUTLINES.foundation} text-route`,
    mark: `${LEGEND_MARK} ${STAMP_OUTLINES.foundation} bg-route-soft`,
    ground: `${TICKET_GROUND} [--ground:color-mix(in_srgb,var(--route)_8%,transparent)]`,
  },
};

export const RELEVANCES = Object.keys(RELEVANCE_TONES) as Relevance[];
