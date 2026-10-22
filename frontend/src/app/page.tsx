import type { Metadata } from "next";

import { HeroTickets } from "@/components/hero-tickets";
import { Introduction } from "@/components/introduction";
import { LoginRequired } from "@/components/login-required";
import { Kicker } from "@/components/kicker";
import { PlanForm } from "@/components/plan-form";
import { DEPARTMENT_NAME } from "@/lib/labels";
import { CATCHPHRASE, INDEXED, SUBHEAD } from "@/lib/site";

export const metadata: Metadata = { robots: INDEXED };

export default function Home() {
  return (
    <div className="grid gap-10">
      <section className="grid gap-x-8 gap-y-7 motion-safe:animate-rise md:grid-cols-[minmax(0,1fr)_auto] md:items-center lg:gap-x-12">
        <div className="grid gap-3">
          <Kicker>立命館大学 理工学部 {DEPARTMENT_NAME}</Kicker>
          <h1 className="font-serif text-3xl leading-snug font-extrabold sm:text-4xl sm:leading-tight lg:text-5xl">
            {CATCHPHRASE.map((part) => (
              <span
                key={part}
                className="inline-block [overflow-wrap:anywhere] [word-break:auto-phrase]"
              >
                {part}
              </span>
            ))}
          </h1>
          <p className="max-w-2xl leading-relaxed text-balance text-sub">
            {SUBHEAD}
          </p>
        </div>
        <HeroTickets />
      </section>
      <LoginRequired signedOut={<Introduction />}>
        <PlanForm />
      </LoginRequired>
    </div>
  );
}
