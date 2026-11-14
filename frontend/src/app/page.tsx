import type { Metadata } from "next";
import localFont from "next/font/local";

import { HeroTickets } from "@/components/hero-tickets";
import { Introduction } from "@/components/introduction";
import { LoginRequired } from "@/components/login-required";
import { Kicker } from "@/components/kicker";
import { Phrases } from "@/components/phrases";
import { PlanForm } from "@/components/plan-form";
import { DEPARTMENT_NAME } from "@/lib/labels";
import { CATCHPHRASE, INDEXED, SUBHEAD } from "@/lib/site";

export const metadata: Metadata = { robots: INDEXED };

const catchphraseFont = localFont({
  src: "../fonts/catchphrase.woff2",
  weight: "800",
  display: "swap",
  variable: "--font-catchphrase-subset",
});

export default function Home() {
  return (
    <div className="grid gap-10">
      <section className="grid grid-cols-[minmax(0,1fr)] gap-x-8 gap-y-7 md:grid-cols-[minmax(0,1fr)_auto] md:items-center lg:gap-x-12">
        <div className="grid gap-3">
          <Kicker>立命館大学 理工学部 {DEPARTMENT_NAME}</Kicker>
          <h1
            className={`${catchphraseFont.variable} font-catchphrase text-3xl leading-snug font-extrabold sm:text-4xl sm:leading-tight lg:text-5xl`}
          >
            <Phrases parts={CATCHPHRASE} />
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
