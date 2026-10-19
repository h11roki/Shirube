import { type ReactNode, Suspense } from "react";

import { SignInButton } from "@/components/account";
import { currentSession } from "@/lib/session";

export function LoginRequired({ children }: { children: ReactNode }) {
  return (
    <Suspense fallback={<p className="text-sm text-sub">読み込んでいます</p>}>
      <SessionGate>{children}</SessionGate>
    </Suspense>
  );
}

async function SessionGate({ children }: { children: ReactNode }) {
  const session = await currentSession();
  if (session?.googleSubject) {
    return children;
  }
  return (
    <section className="grid justify-items-start gap-4 rounded-lg border border-line bg-sheet p-6 text-sm shadow-paper">
      <p>道標を作ったり見返したりするには、Google でログインしてください。</p>
      <SignInButton />
    </section>
  );
}
