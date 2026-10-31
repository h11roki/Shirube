import type { Metadata } from "next";

import { LoginRequired } from "@/components/login-required";
import { PlanList } from "@/components/plan-list";
import { MY_PLANS_LABEL } from "@/lib/labels";

export const metadata: Metadata = { title: MY_PLANS_LABEL };

export default function Plans() {
  return (
    <div className="space-y-6">
      <h1 className="font-serif text-3xl font-extrabold">{MY_PLANS_LABEL}</h1>
      <LoginRequired>
        <PlanList />
      </LoginRequired>
    </div>
  );
}
