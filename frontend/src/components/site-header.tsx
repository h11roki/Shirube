import Link from "next/link";
import { Suspense } from "react";

import { Account } from "@/components/account";
import { NAV_LINK } from "@/components/styles";

export function SiteHeader() {
  return (
    <header className="border-b border-line">
      <div className="mx-auto flex max-w-5xl flex-wrap items-baseline justify-between gap-x-6 gap-y-2 px-4 pt-5 pb-4 sm:px-6">
        <Link href="/" className="flex items-baseline gap-2">
          <span className="font-serif text-2xl font-extrabold tracking-wide">
            shirube
          </span>
          <span className="text-[11px] tracking-[0.3em] text-sub">道標</span>
        </Link>
        <nav className="flex flex-wrap items-center gap-x-5 gap-y-1 text-sm text-sub">
          <Link href="/" className={NAV_LINK}>
            道標を作る
          </Link>
          <Link href="/plans" className={NAV_LINK}>
            自分の道標
          </Link>
          <Suspense fallback={null}>
            <Account />
          </Suspense>
        </nav>
      </div>
    </header>
  );
}
