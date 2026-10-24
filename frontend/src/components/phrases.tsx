import { Fragment } from "react";

export function Phrases({ parts }: { parts: readonly string[] }) {
  return (
    <span className="[overflow-wrap:anywhere] [word-break:keep-all]">
      {parts.map((part, index) => (
        <Fragment key={index}>
          {index > 0 && <wbr aria-hidden />}
          {part}
        </Fragment>
      ))}
    </span>
  );
}
