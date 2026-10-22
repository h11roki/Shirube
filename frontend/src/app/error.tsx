"use client";

import Link from "next/link";
import { useEffect } from "react";

import { OUTLINE_BUTTON, TEXT_LINK } from "@/components/styles";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("画面を描けませんでした", error);
  }, [error]);

  return (
    <section
      role="alert"
      className="mx-auto grid max-w-xl justify-items-start gap-3 rounded-lg border border-danger/30 bg-danger-soft p-6 text-sm"
    >
      <h1 className="font-serif text-xl font-bold text-danger">
        うまく表示できませんでした
      </h1>
      <p>もう一度試しても直らなければ、しばらくしてから開いてください。</p>
      <div className="flex flex-wrap items-center gap-4">
        <button type="button" onClick={reset} className={OUTLINE_BUTTON}>
          もう一度試す
        </button>
        <Link href="/" className={TEXT_LINK}>
          トップへ
        </Link>
      </div>
    </section>
  );
}
