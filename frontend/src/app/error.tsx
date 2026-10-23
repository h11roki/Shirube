"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { startTransition } from "react";

import { Notice } from "@/components/notice";
import { OUTLINE_BUTTON, STANDALONE_LINK } from "@/components/styles";

export default function ErrorPage({ reset }: { reset: () => void }) {
  const pathname = usePathname();
  const router = useRouter();
  return (
    <Notice title="うまく表示できませんでした">
      <p>もう一度試しても直らなければ、しばらくしてから開いてください。</p>
      <div className="flex flex-wrap items-center gap-4">
        <button
          type="button"
          onClick={() =>
            startTransition(() => {
              router.refresh();
              reset();
            })
          }
          className={OUTLINE_BUTTON}
        >
          もう一度試す
        </button>
        {pathname !== "/" && (
          <Link href="/" className={STANDALONE_LINK}>
            トップへ
          </Link>
        )}
      </div>
    </Notice>
  );
}
