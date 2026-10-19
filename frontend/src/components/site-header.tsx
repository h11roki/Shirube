import Link from "next/link";
import { Suspense } from "react";

import { Account } from "@/components/account";

export function SiteHeader() {
  return (
    <header className="border-b border-stone-200 bg-white">
      <div className="mx-auto flex max-w-4xl flex-wrap items-center justify-between gap-x-6 gap-y-2 px-4 py-3 sm:px-6">
        <Link href="/" className="flex items-baseline gap-2">
          <span className="text-lg font-bold tracking-tight text-stone-900">
            shirube
          </span>
          <span className="text-xs text-stone-500">道標</span>
        </Link>
        <nav className="flex items-center gap-4 text-sm">
          <Link href="/" className="text-stone-700 hover:text-teal-800">
            道標を作る
          </Link>
          <Link href="/plans" className="text-stone-700 hover:text-teal-800">
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
