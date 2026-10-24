import type { ReactNode } from "react";

import { Phrases } from "@/components/phrases";
import { plateParts } from "@/lib/words";

export function DestinationName({
  destination,
  children,
}: {
  destination: string;
  children: ReactNode;
}) {
  const { words, tail } = plateParts(destination);
  return (
    <>
      <Phrases parts={words} />
      <span className="whitespace-nowrap">
        {tail}
        {children}
      </span>
    </>
  );
}
