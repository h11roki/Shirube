import { Kicker } from "@/components/kicker";
import { Phrases } from "@/components/phrases";
import { RELEVANCE_TONES } from "@/components/relevance-tones";
import { TICKET_NOTCH } from "@/components/styles";
import { Tilt } from "@/components/tilt";
import type { Relevance } from "@/lib/api/client";
import { RELEVANCE_LABELS, sampleLabel } from "@/lib/labels";
import { SAMPLE_PLAN } from "@/lib/sample-plan";
import { SAMPLE_TICKETS } from "@/lib/sample-tickets";
import { stampTilt } from "@/lib/ticket-face";
import { wordsOf } from "@/lib/words";

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
                  className={`relative grid grid-cols-[minmax(0,1fr)_var(--stub)] border border-line bg-note [--stub:3.625rem] md:[--stub:4.375rem] ${RELEVANCE_TONES[course.relevance].ground} ${core ? "motion-safe:animate-thud" : ""}`}
                >
                  <div className="grid gap-0.5 px-3.5 py-3 md:px-4 md:pt-3.5 md:pb-4">
                    <p className="pr-9 text-lg leading-snug font-bold md:pr-10 md:text-[1.3125rem]">
                      <Phrases parts={wordsOf(course.name)} />
                    </p>
                    <p className="text-xs leading-relaxed text-sub md:text-fine">
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
                        <dt className="text-label tracking-[0.14em] text-sub">
                          {label}
                        </dt>
                        <dd className="text-sm font-bold md:text-base">
                          {value}
                        </dd>
                      </div>
                    ))}
                  </dl>
                  <span
                    style={{
                      rotate: `${stampTilt(course.name)}deg`,
                      animationDelay: core ? `${STAMP_DELAY_MS}ms` : undefined,
                    }}
                    className={`top-2.5 right-[calc(var(--stub)+0.75rem)] size-8 text-[0.9375rem] md:size-9 md:text-base ${RELEVANCE_TONES[course.relevance].stamp} ${core ? "motion-safe:animate-stamp" : ""}`}
                  >
                    {RELEVANCE_LABELS[course.relevance]}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </Tilt>
      <Kicker>{sampleLabel(SAMPLE_PLAN.conditions.occupation)}</Kicker>
    </div>
  );
}
