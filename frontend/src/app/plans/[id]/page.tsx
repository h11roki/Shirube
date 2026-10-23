import type { Metadata } from "next";

import { LoginRequired } from "@/components/login-required";
import { PlanView } from "@/components/plan-view";
import { PLAN_PAGE_TITLE } from "@/lib/labels";

export const metadata: Metadata = { title: PLAN_PAGE_TITLE };

export default function PlanPage() {
  return (
    <LoginRequired heading="h1">
      <PlanView />
    </LoginRequired>
  );
}
