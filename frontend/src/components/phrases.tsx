import { Fragment } from "react";

export function Phrases({
  parts,
  spokenPrefix = "",
}: {
  parts: readonly string[];
  spokenPrefix?: string;
}) {
  return (
    <>
      <span className="sr-only">{`${spokenPrefix}${parts.join("")}`}</span>
      <span
        aria-hidden
        className="[overflow-wrap:anywhere] [word-break:keep-all]"
      >
        {parts.map((part, index) => (
          <Fragment key={index}>
            {index > 0 && <wbr />}
            {part}
          </Fragment>
        ))}
      </span>
    </>
  );
}
