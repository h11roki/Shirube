import { Fragment } from "react";

import { bracketRuns } from "@/lib/words";

export function Phrases({ parts }: { parts: readonly string[] }) {
  return (
    <span className="[overflow-wrap:anywhere] [word-break:keep-all]">
      {parts.map((part, index) => (
        <Fragment key={index}>
          {index > 0 && <wbr aria-hidden />}
          {bracketRuns(part).map((run, runIndex) =>
            run.nowrap ? (
              <span key={runIndex} className="whitespace-nowrap">
                {run.text}
              </span>
            ) : (
              <Fragment key={runIndex}>{run.text}</Fragment>
            ),
          )}
        </Fragment>
      ))}
    </span>
  );
}
