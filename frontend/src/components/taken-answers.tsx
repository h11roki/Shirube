"use client";

import { createContext, useContext } from "react";

export type TakenAnswers = {
  asked: ReadonlySet<string>;
  busy: boolean;
  answer: (name: string, taken: boolean) => void;
};

export const TakenAnswersContext = createContext<TakenAnswers | null>(null);

export function useTakenAnswers(): TakenAnswers | null {
  return useContext(TakenAnswersContext);
}
