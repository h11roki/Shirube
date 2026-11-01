"use client";

import { createContext } from "react";

import type { TakenChange } from "@/lib/labels";

export type TakenAnswers = {
  asked: ReadonlySet<string>;
  busy: boolean;
  tearing: string | null;
  answer: (name: string, change: TakenChange) => void;
};

export const TakenAnswersContext = createContext<TakenAnswers | null>(null);
