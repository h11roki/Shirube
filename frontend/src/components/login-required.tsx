import { type ReactNode, Suspense } from "react";

import { SignInButton } from "@/components/account";
import { SignedOutGate } from "@/components/signed-out-gate";
import { currentSession } from "@/lib/session";

type Gate = {
  children: ReactNode;
  signedOut?: ReactNode;
  heading?: "h1" | "h2";
};

export function LoginRequired({ children, signedOut, heading }: Gate) {
  return (
    <Suspense fallback={<p className="text-sm text-sub">読み込んでいます</p>}>
      <SessionGate signedOut={signedOut} heading={heading}>
        {children}
      </SessionGate>
    </Suspense>
  );
}

async function SessionGate({ children, signedOut, heading }: Gate) {
  const session = await currentSession();
  if (session?.googleSubject) {
    return <SignedOutGate heading={heading}>{children}</SignedOutGate>;
  }
  return (
    signedOut ?? (
      <section className="grid justify-items-start gap-4 rounded-lg border border-line bg-sheet p-6 text-sm shadow-paper">
        <p>道標を作ったり見返したりするには、Google でログインしてください。</p>
        <SignInButton />
      </section>
    )
  );
}
