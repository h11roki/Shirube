import type { Metadata } from "next";
import { Suspense } from "react";

import { LoginRequired } from "@/components/login-required";
import { PlanList } from "@/components/plan-list";

export const metadata: Metadata = { title: "自分の道標 | shirube" };

export default function Plans() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">自分の道標</h1>
      <Suspense
        fallback={<p className="text-sm text-stone-500">読み込んでいます</p>}
      >
        <LoginRequired>
          <PlanList />
        </LoginRequired>
      </Suspense>
    </div>
  );
}
