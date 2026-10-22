"use client";

import { type ReactNode, useSyncExternalStore } from "react";

import { Notice } from "@/components/notice";
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
    <Notice title="ログインが切れました" heading="h2">
      <p>ログインし直すと、この画面の続きから使えます。</p>
      <button
        type="button"
        onClick={() => window.location.reload()}
        className={OUTLINE_BUTTON}
      >
        {SIGN_IN_AGAIN_LABEL}
      </button>
    </Notice>
  );
}
