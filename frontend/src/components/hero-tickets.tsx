"use client";

import { RELEVANCE_TONES } from "@/components/relevance-tones";
import { TICKET_NOTCH, TICKET_STAMP } from "@/components/styles";
import type { Relevance } from "@/lib/api/client";
import { RELEVANCE_LABELS, slotsLabel } from "@/lib/labels";
import { SAMPLE_TICKETS, lastSentence } from "@/lib/sample-tickets";

const PLACES: Record<Relevance, string> = {
  foundation:
    "top-0 left-0 rotate-[4deg] motion-safe:animate-deal-back motion-safe:group-hover:-translate-x-2 motion-safe:group-hover:-translate-y-2 motion-safe:group-hover:rotate-[7deg]",
  core: "top-[82px] left-6 rotate-[-3deg] motion-safe:animate-deal-front motion-safe:group-hover:translate-x-2.5 motion-safe:group-hover:translate-y-1 motion-safe:group-hover:rotate-[-6deg] md:top-[94px] md:left-9",
};

export function HeroTickets() {
  return (
    <div
      aria-hidden
      onPointerMove={(event) => {
        if (event.pointerType !== "mouse") return;
        const box = event.currentTarget.getBoundingClientRect();
        const x = (event.clientX - box.left) / box.width - 0.5;
        const y = (event.clientY - box.top) / box.height - 0.5;
        event.currentTarget.style.setProperty("--tilt-x", `${-y * 8}deg`);
        event.currentTarget.style.setProperty("--tilt-y", `${x * 10}deg`);
      }}
      onPointerLeave={(event) => {
        event.currentTarget.style.removeProperty("--tilt-x");
        event.currentTarget.style.removeProperty("--tilt-y");
      }}
      className="group relative h-[200px] w-full max-w-[318px] max-[359px]:origin-top-left max-[359px]:scale-90 motion-safe:transition-transform motion-safe:duration-200 motion-safe:ease-out motion-safe:[transform:perspective(900px)_rotateX(var(--tilt-x,0deg))_rotateY(var(--tilt-y,0deg))] md:h-[230px] md:w-[336px] md:max-w-none"
    >
      {SAMPLE_TICKETS.map((course) => {
        const core = course.relevance === "core";
        return (
          <div
            key={course.name}
            className={`absolute w-[262px] motion-safe:transition-transform motion-safe:duration-300 md:w-[300px] ${PLACES[course.relevance]}`}
          >
            <div
              className={`relative grid grid-cols-[minmax(0,1fr)_58px] rounded-lg border border-line bg-note shadow-[0_4px_10px_var(--shadow),0_14px_30px_var(--shadow)] motion-safe:transition-shadow motion-safe:duration-300 motion-safe:group-hover:shadow-[0_8px_16px_var(--shadow),0_22px_40px_var(--shadow)] md:grid-cols-[minmax(0,1fr)_70px] ${core ? "motion-safe:animate-thud" : ""}`}
            >
              <div className="grid min-w-0 content-start gap-0.5 px-3.5 py-3 md:px-4 md:pt-3.5 md:pb-4">
                <p
                  className={`text-[11px] font-bold tracking-[0.14em] md:text-xs ${RELEVANCE_TONES[course.relevance].text}`}
                >
                  {RELEVANCE_LABELS[course.relevance]}
                </p>
                <p
                  className={`text-lg leading-snug font-bold md:text-[21px] ${core ? "pr-9 md:pr-10" : ""}`}
                >
                  {course.name}
                </p>
                <p className="text-xs leading-relaxed text-sub md:text-[13px]">
                  {lastSentence(course.reason)}
                </p>
              </div>
              <dl
                className={`relative grid content-center gap-2 border-l-2 border-dashed border-line text-center tabular-nums ${TICKET_NOTCH}`}
              >
                <div>
                  <dt className="text-[9.5px] tracking-[0.14em] text-sub">
                    コマ
                  </dt>
                  <dd className="text-sm font-bold md:text-base">
                    {slotsLabel(course)}
                  </dd>
                </div>
                <div>
                  <dt className="text-[9.5px] tracking-[0.14em] text-sub">
                    単位
                  </dt>
                  <dd className="text-sm font-bold md:text-base">
                    {course.credits}
                  </dd>
                </div>
              </dl>
              {core && (
                <span
                  className={`size-8 text-[15px] motion-safe:animate-stamp md:size-9 md:text-base ${TICKET_STAMP} right-[4.4rem] md:right-[5.1rem]`}
                >
                  {RELEVANCE_LABELS.core}
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
