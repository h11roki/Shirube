"use client";

import { type ReactNode, useEffect, useState } from "react";

import { Notice } from "@/components/notice";
import { OUTLINE_BUTTON } from "@/components/styles";
import { subscribeSignedOut } from "@/lib/api/client";
import { SIGN_IN_AGAIN_LABEL } from "@/lib/labels";

export function SignedOutGate({
  heading = "h2",
  children,
}: {
  heading?: "h1" | "h2";
  children: ReactNode;
}) {
  const [signedOut, setSignedOut] = useState(false);

  useEffect(() => subscribeSignedOut(() => setSignedOut(true)), []);

  if (!signedOut) {
    return children;
  }
  return (
    <Notice title="ログインが切れました" heading={heading}>
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
