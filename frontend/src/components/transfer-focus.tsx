"use client";

import { createContext, useContext } from "react";

import type { Transfer } from "@/lib/roadmap";

export type TransferFocus = {
  focus: string | null;
  linked: Set<string>;
  hover: (name: string | null) => void;
  follow: (from: string, transfer: Transfer) => void;
};

export const TransferFocusContext = createContext<TransferFocus | null>(null);

export function useTransferFocus(): TransferFocus | null {
  return useContext(TransferFocusContext);
}
