"use client";

import { type ReactNode, useSyncExternalStore } from "react";

import { OUTLINE_BUTTON } from "@/components/styles";
import { hasSignedOut, subscribeSignedOut } from "@/lib/api/client";
import { SIGN_IN_AGAIN_LABEL } from "@/lib/labels";

export function SignedOutGate({ children }: { children: ReactNode }) {
  const signedOut = useSyncExternalStore(
    subscribeSignedOut,
    hasSignedOut,
    () => false,
  );
  if (!signedOut) {
    return children;
  }
  return (
    <section
      role="alert"
      className="mx-auto grid max-w-xl justify-items-start gap-3 rounded-lg border border-danger/30 bg-danger-soft p-6 text-sm"
    >
      <h2 className="font-serif text-xl font-bold text-danger">
        ログインが切れました
      </h2>
      <p>ログインし直すと、この画面の続きから使えます。</p>
      <button
        type="button"
        onClick={() => window.location.reload()}
        className={OUTLINE_BUTTON}
      >
        {SIGN_IN_AGAIN_LABEL}
      </button>
    </section>
  );
}
