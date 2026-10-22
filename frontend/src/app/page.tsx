import type { Metadata } from "next";

import { Introduction } from "@/components/introduction";
import { LoginRequired } from "@/components/login-required";
import { Kicker } from "@/components/kicker";
import { PlanForm } from "@/components/plan-form";
import { DEPARTMENT_NAME } from "@/lib/labels";
import { INDEXED } from "@/lib/site";

export const metadata: Metadata = { robots: INDEXED };

export default function Home() {
  return (
    <div className="grid gap-10">
      <section className="grid gap-3 motion-safe:animate-rise">
        <Kicker>立命館大学 理工学部 {DEPARTMENT_NAME}</Kicker>
        <h1 className="font-serif text-3xl leading-snug font-extrabold sm:text-5xl sm:leading-tight">
          <span className="inline-block max-w-full">履修に迷ったら、</span>
          <span className="inline-block max-w-full">なりたい職業から。</span>
        </h1>
        <p className="max-w-2xl leading-relaxed text-sub">
          シラバスから職業に関係の深い授業を選び、取る理由をつけて、卒業までの学期ごとの時間割に並べます。
        </p>
      </section>
      <LoginRequired signedOut={<Introduction />}>
        <PlanForm />
      </LoginRequired>
    </div>
  );
}
