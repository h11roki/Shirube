import { Introduction } from "@/components/introduction";
import { LoginRequired } from "@/components/login-required";
import { PlanForm } from "@/components/plan-form";

export default function Home() {
  return (
    <div className="grid gap-10">
      <section className="grid gap-3 motion-safe:animate-rise">
        <p className="text-xs font-bold tracking-[0.28em] text-pillar">
          立命館大学 理工学部 電子情報工学科
        </p>
        <h1 className="font-serif text-3xl leading-snug font-extrabold text-balance sm:text-5xl sm:leading-tight">
          なりたい職業から、卒業までの道標を作る
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
