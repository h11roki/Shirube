"use client";

import { createContext, useContext, useMemo, useState } from "react";

import type { SemesterPlan } from "@/lib/api/client";
import { REDUCED_MOTION } from "@/lib/motion";
import { type Hop, type TransferRoutes, linkedNames } from "@/lib/roadmap";

export type Trip = { from: Hop; to: Hop; button: string };

export type TransferFocus = {
  focus: string | null;
  linked: Set<string>;
  hover: (name: string | null) => void;
  select: (name: string | null) => void;
  reachable: (hop: Hop) => boolean;
  trip: Trip | null;
  follow: (trip: Trip) => void;
  back: () => void;
};

export const TransferFocusContext = createContext<TransferFocus | null>(null);

export function useTransferFocus(): TransferFocus | null {
  return useContext(TransferFocusContext);
}

export function useTransferFocusValue(
  routes: TransferRoutes,
  reachable: (hop: Hop) => boolean,
  go: (focusId: string, semester: SemesterPlan) => void,
): TransferFocus {
  const [hovered, setHovered] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [trip, setTrip] = useState<Trip | null>(null);
  const [tripRoutes, setTripRoutes] = useState(routes);
  if (tripRoutes !== routes) {
    setTripRoutes(routes);
    setTrip(null);
  }
  const focus = hovered ?? selected;

  return useMemo(
    () => ({
      focus,
      linked: linkedNames(routes, focus),
      hover: setHovered,
      select: setSelected,
      reachable,
      trip,
      follow: (next) => {
        setHovered(null);
        setTrip(next);
        go(ticketHeadingId(next.to.section), next.to.semester);
      },
      back: () => {
        if (trip) {
          setHovered(null);
          setTrip(null);
          go(trip.button, trip.from.semester);
        }
      },
    }),
    [routes, focus, reachable, go, trip],
  );
}

export function ticketHeadingId(section: string): string {
  return `ticket-${section}-name`;
}

export function revealElement(id: string) {
  const element = document.getElementById(id);
  element?.scrollIntoView({
    block: "center",
    behavior: matchMedia(REDUCED_MOTION).matches ? "instant" : "smooth",
  });
  element?.focus({ preventScroll: true });
}
