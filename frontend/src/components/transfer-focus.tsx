"use client";

import { createContext, useContext, useMemo, useState } from "react";

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
  go: (hop: Hop, focusId: string) => void,
): TransferFocus {
  const [hovered, setHovered] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [trip, setTrip] = useState<Trip | null>(null);
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
        setTrip(next);
        go(next.to, ticketHeadingId(next.to.section));
      },
      back: () => {
        if (trip) {
          setTrip(null);
          go(trip.from, trip.button);
        }
      },
    }),
    [routes, focus, reachable, go, trip],
  );
}

export function ticketHeadingId(section: string): string {
  return `ticket-${section}-name`;
}
