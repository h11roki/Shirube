import type { Metadata } from "next";
import { Suspense } from "react";

import { LoginRequired } from "@/components/login-required";
import { PlanView } from "@/components/plan-view";

export const metadata: Metadata = { title: "道標 | shirube" };

export default function PlanPage() {
  return (
    <Suspense
      fallback={<p className="text-sm text-stone-500">読み込んでいます</p>}
    >
      <LoginRequired>
        <PlanView />
      </LoginRequired>
    </Suspense>
  );
}
