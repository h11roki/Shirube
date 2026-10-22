import type { Metadata } from "next";

import { LoginRequired } from "@/components/login-required";
import { PlanView } from "@/components/plan-view";

export const metadata: Metadata = { title: "道標" };

export default function PlanPage() {
  return (
    <LoginRequired heading="h1">
      <PlanView />
    </LoginRequired>
  );
}
