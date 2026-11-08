import Link from "next/link";
import { Suspense } from "react";

import { CREATE_PLAN_LABEL } from "@/lib/labels";
import { currentSession } from "@/lib/session";
import { LOGIN_PATH } from "@/lib/site";

type Look = { className: string };

export function CreatePlanLink({ className }: Look) {
  return (
    <Suspense
      fallback={<PlanFormLink href={LOGIN_PATH} className={className} />}
    >
      <SessionPlanFormLink className={className} />
    </Suspense>
  );
}

async function SessionPlanFormLink({ className }: Look) {
  const session = await currentSession();
  return (
    <PlanFormLink
      href={session?.googleSubject ? "/" : LOGIN_PATH}
      className={className}
    />
  );
}

function PlanFormLink({ href, className }: Look & { href: string }) {
  return (
    <Link href={href} className={className}>
      {CREATE_PLAN_LABEL}
    </Link>
  );
}
