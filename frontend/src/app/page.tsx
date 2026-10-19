import { LoginRequired } from "@/components/login-required";
import { PlanForm } from "@/components/plan-form";

export default function Home() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-bold tracking-tight text-balance">
          なりたい職業から、卒業までの道標を作る
        </h1>
        <p className="text-sm text-stone-600">
          職業に要るスキルを読み取り、シラバスから関係の深い授業を選んで、卒業までの時間割に並べます。
        </p>
      </div>
      <LoginRequired>
        <PlanForm />
      </LoginRequired>
    </div>
  );
}
