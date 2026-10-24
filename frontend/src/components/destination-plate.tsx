import { Fragment } from "react";

import { plateParts } from "@/lib/words";

export function DestinationPlate({ destination }: { destination: string }) {
  const { words, tail } = plateParts(destination);
  return (
    <p
      aria-hidden
      className="inline-block justify-self-start rounded-md border border-line bg-plate px-5 py-2 text-plate-ink shadow-paper"
    >
      <span className="block font-serif text-[clamp(1.125rem,5.9vw,1.5rem)] leading-snug font-extrabold tracking-wide text-balance [overflow-wrap:anywhere] [word-break:keep-all] sm:text-3xl">
        {words.map((word, index) => (
          <Fragment key={index}>
            {index > 0 && <wbr />}
            {word}
          </Fragment>
        ))}
        <span className="whitespace-nowrap">
          {tail}
          <span className="ml-1.5 text-plate-accent">行</span>
        </span>
      </span>
    </p>
  );
}
