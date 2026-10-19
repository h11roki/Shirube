"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { type Transfer, linkedNames } from "@/lib/roadmap";

const FOLLOW_MS = 2500;

export type TransferFocus = {
  focus: string | null;
  linked: Set<string>;
  hover: (name: string | null) => void;
  select: (name: string | null) => void;
  reachable: (transfer: Transfer) => boolean;
  follow: (from: string, transfer: Transfer) => void;
};

export const TransferFocusContext = createContext<TransferFocus | null>(null);

export function useTransferFocus(): TransferFocus | null {
  return useContext(TransferFocusContext);
}

export function useTransferFocusValue(
  found: Map<string, Transfer>,
  reachable: (transfer: Transfer) => boolean,
  go: (transfer: Transfer) => void,
): TransferFocus {
  const [hovered, setHovered] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [followed, setFollowed] = useState<string | null>(null);
  const release = useRef<ReturnType<typeof setTimeout>>(undefined);
  const focus = hovered ?? followed ?? selected;

  useEffect(() => () => clearTimeout(release.current), []);

  return useMemo(
    () => ({
      focus,
      linked: linkedNames(found, focus),
      hover: setHovered,
      select: setSelected,
      reachable,
      follow: (from, transfer) => {
        clearTimeout(release.current);
        setFollowed(from);
        go(transfer);
        release.current = setTimeout(() => setFollowed(null), FOLLOW_MS);
      },
    }),
    [found, focus, reachable, go],
  );
}
