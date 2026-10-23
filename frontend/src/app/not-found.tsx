import type { Metadata } from "next";
import Link from "next/link";

import { STANDALONE_LINK } from "@/components/styles";

export const metadata: Metadata = { title: "ページが見つかりません" };

export default function NotFound() {
  return (
    <section className="mx-auto grid max-w-xl justify-items-start gap-3 rounded-lg border border-line bg-sheet p-6 text-sm shadow-paper">
      <h1 className="font-serif text-xl font-bold">ページが見つかりません</h1>
      <p>この先に駅はありません。URL を確かめるか、トップへ戻ってください。</p>
      <Link href="/" className={STANDALONE_LINK}>
        道標を作る
      </Link>
    </section>
  );
}
