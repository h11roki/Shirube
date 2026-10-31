import { TICKET_SEAL, TICKET_STAMP } from "@/components/styles";
import type { Relevance } from "@/lib/api/client";

export const RELEVANCE_TONES: Record<
  Relevance,
  {
    text: string;
    fill: string;
    sticky: string;
    stamp: string;
    mark: string;
    ground: string;
  }
> = {
  core: {
    text: "text-pillar",
    fill: "bg-pillar",
    sticky: "rotate-[0.4deg] bg-pillar-soft",
    stamp: TICKET_STAMP,
    mark: "rounded-full border border-pillar shadow-[inset_0_0_0_1.5px_var(--paper),inset_0_0_0_2.25px_var(--pillar)]",
    ground:
      "bg-[repeating-linear-gradient(45deg,color-mix(in_srgb,var(--pillar)_7%,transparent)_0_0.5px,transparent_0.5px_4px)]",
  },
  foundation: {
    text: "text-route",
    fill: "bg-route",
    sticky: "rotate-[-0.4deg] bg-route-soft",
    stamp: TICKET_SEAL,
    mark: "border border-route shadow-[inset_0_0_0_1.5px_var(--paper),inset_0_0_0_2.25px_var(--route)]",
    ground:
      "bg-[repeating-linear-gradient(45deg,color-mix(in_srgb,var(--route)_8%,transparent)_0_0.5px,transparent_0.5px_4px)]",
  },
};

export const RELEVANCES = Object.keys(RELEVANCE_TONES) as Relevance[];
