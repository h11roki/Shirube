import type { Metadata } from "next";

import { LoginRequired } from "@/components/login-required";
import { PlanList } from "@/components/plan-list";

export const metadata: Metadata = { title: "自分の道標" };

export default function Plans() {
  return (
    <div className="space-y-6">
      <h1 className="font-serif text-3xl font-extrabold">自分の道標</h1>
      <LoginRequired>
        <PlanList />
      </LoginRequired>
    </div>
  );
}
