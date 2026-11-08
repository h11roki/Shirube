import Link from "next/link";
import { Suspense } from "react";

import { Account } from "@/components/account";
import { NAV_LINK } from "@/components/styles";
import { ThemeToggle } from "@/components/theme-toggle";
import { MY_PLANS_LABEL } from "@/lib/labels";
import { currentSession } from "@/lib/session";

const CREATE_PLAN_LABEL = "道標を作る";

export function SiteHeader() {
  return (
    <header className="border-b border-line">
      <div className="mx-auto flex max-w-5xl flex-wrap items-baseline gap-x-6 gap-y-2 px-4 pt-5 pb-4 sm:px-6">
        <Link href="/" className="flex items-baseline gap-2">
          <span className="font-serif text-2xl font-extrabold tracking-wide">
            shirube
          </span>
          <span className="text-label tracking-[0.3em] text-sub">道標</span>
        </Link>
        <div className="ml-auto self-center">
          <ThemeToggle />
        </div>
        <nav className="flex w-full flex-wrap items-center gap-x-5 gap-y-1 text-sm text-sub lg:w-auto">
          <Suspense
            fallback={
              <Link href="/" className={NAV_LINK}>
                {CREATE_PLAN_LABEL}
              </Link>
            }
          >
            <CreatePlanLink />
          </Suspense>
          <Link href="/plans" className={NAV_LINK}>
            {MY_PLANS_LABEL}
          </Link>
          <Suspense fallback={null}>
            <Account />
          </Suspense>
        </nav>
      </div>
    </header>
  );
}

async function CreatePlanLink() {
  const session = await currentSession();
  return (
    <Link href={session?.googleSubject ? "/" : "/login"} className={NAV_LINK}>
      {CREATE_PLAN_LABEL}
    </Link>
  );
}
