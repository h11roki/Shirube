import type { ReactNode } from "react";

import { Phrases } from "@/components/phrases";
import { splitTail } from "@/lib/words";

export function DestinationName({
  words,
  children,
}: {
  words: readonly string[];
  children: ReactNode;
}) {
  const parts = splitTail(words);
  return (
    <span className="[word-break:keep-all]">
      <Phrases parts={parts.words} />
      <span className="whitespace-nowrap">
        {parts.tail}
        {children}
      </span>
    </span>
  );
}
