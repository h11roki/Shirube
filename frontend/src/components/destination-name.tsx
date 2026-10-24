import type { ReactNode } from "react";

import { Phrases } from "@/components/phrases";
import type { DestinationParts } from "@/lib/words";

export function DestinationName({
  parts,
  children,
}: {
  parts: DestinationParts;
  children: ReactNode;
}) {
  return (
    <>
      <Phrases parts={parts.words} />
      <span className="whitespace-nowrap">
        {parts.tail}
        {children}
      </span>
    </>
  );
}
