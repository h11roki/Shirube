import { RELEVANCE_TONES } from "@/components/relevance-tones";
import { PHRASE_WRAP, TICKET_NOTCH, TICKET_STAMP } from "@/components/styles";
import { Tilt } from "@/components/tilt";
import type { Relevance } from "@/lib/api/client";
import { RELEVANCE_LABELS, sampleLabel } from "@/lib/labels";
import { SAMPLE_PLAN } from "@/lib/sample-plan";
import { SAMPLE_TICKETS } from "@/lib/sample-tickets";

const PLACES: Record<Relevance, string> = {
  foundation:
    "max-w-full rotate-[4deg] motion-safe:animate-deal-back motion-safe:group-hover:-translate-x-2 motion-safe:group-hover:-translate-y-2 motion-safe:group-hover:rotate-[7deg]",
  core: "mt-0.5 ml-6 max-w-[calc(100%-1.5rem)] rotate-[-3deg] motion-safe:animate-deal-front motion-safe:group-hover:translate-x-2.5 motion-safe:group-hover:translate-y-1 motion-safe:group-hover:rotate-[-6deg] md:ml-9 md:max-w-[calc(100%-2.25rem)]",
};
const DEAL_DELAY_MS: Record<Relevance, number> = { foundation: 100, core: 280 };
const STAMP_DELAY_MS = 1000;
const THUD_DELAY_MS = STAMP_DELAY_MS + 60;

export function HeroTickets() {
  return (
    <div aria-hidden className="flex flex-col gap-3">
      <Tilt className="group max-w-[19.875rem] md:w-[21rem] md:max-w-none">
        <div className="flex flex-col motion-safe:transition-transform motion-safe:duration-200 motion-safe:ease-out motion-safe:[transform:perspective(900px)_rotateX(var(--tilt-x,0deg))_rotateY(var(--tilt-y,0deg))]">
          {SAMPLE_TICKETS.map((course) => {
            const core = course.relevance === "core";
            return (
              <div
                key={course.name}
                style={{
                  animationDelay: `${DEAL_DELAY_MS[course.relevance]}ms`,
                }}
                className={`w-[16.375rem] motion-safe:transition-transform motion-safe:duration-300 md:w-[18.75rem] ${PLACES[course.relevance]}`}
              >
                <div
                  style={
                    core ? { animationDelay: `${THUD_DELAY_MS}ms` } : undefined
                  }
                  className={`relative grid grid-cols-[minmax(0,1fr)_var(--stub)] rounded-lg border border-line bg-note shadow-[0_4px_10px_var(--shadow),0_14px_30px_var(--shadow)] [--stub:3.625rem] motion-safe:transition-shadow motion-safe:duration-300 motion-safe:group-hover:shadow-[0_8px_16px_var(--shadow),0_22px_40px_var(--shadow)] md:[--stub:4.375rem] ${core ? "motion-safe:animate-thud" : ""}`}
                >
                  <div className="grid gap-0.5 px-3.5 py-3 md:px-4 md:pt-3.5 md:pb-4">
                    <p
                      className={`text-[0.6875rem] font-bold tracking-[0.14em] md:text-xs ${RELEVANCE_TONES[course.relevance].text}`}
                    >
                      {RELEVANCE_LABELS[course.relevance]}
                    </p>
                    <p
                      className={`text-lg leading-snug font-bold md:text-[1.3125rem] ${PHRASE_WRAP} ${core ? "pr-9 md:pr-10" : ""}`}
                    >
                      {course.name}
                    </p>
                    <p className="text-xs leading-relaxed text-sub md:text-[0.8125rem]">
                      {course.reason}
                    </p>
                  </div>
                  <dl
                    className={`relative grid content-center gap-2 border-l-2 border-dashed border-line text-center tabular-nums ${TICKET_NOTCH}`}
                  >
                    {(
                      [
                        ["コマ", course.slot],
                        ["単位", course.credits],
                      ] as const
                    ).map(([label, value]) => (
                      <div key={label}>
                        <dt className="text-[0.6875rem] tracking-[0.14em] text-sub">
                          {label}
                        </dt>
                        <dd className="text-sm font-bold md:text-base">
                          {value}
                        </dd>
                      </div>
                    ))}
                  </dl>
                  {core && (
                    <span
                      style={{ animationDelay: `${STAMP_DELAY_MS}ms` }}
                      className={`right-[calc(var(--stub)+0.75rem)] size-8 text-[0.9375rem] motion-safe:animate-stamp md:size-9 md:text-base ${TICKET_STAMP}`}
                    >
                      {RELEVANCE_LABELS.core}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </Tilt>
      <p className="text-xs text-sub">
        {sampleLabel(SAMPLE_PLAN.conditions.occupation)}
      </p>
    </div>
  );
}
