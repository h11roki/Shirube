"use client";

import { type ReactNode, createContext, useContext } from "react";

const CourseWordsContext = createContext<Readonly<Record<string, string[]>>>(
  {},
);

export function CourseWordsProvider({
  words,
  children,
}: {
  words: Readonly<Record<string, string[]>>;
  children: ReactNode;
}) {
  return (
    <CourseWordsContext.Provider value={words}>
      {children}
    </CourseWordsContext.Provider>
  );
}

export function useCourseWords(name: string): readonly string[] {
  return useContext(CourseWordsContext)[name] ?? [name];
}
