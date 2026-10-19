import { type ReactNode, Suspense } from "react";

import { SignInButton } from "@/components/account";
import { currentSession } from "@/lib/session";

export function LoginRequired({ children }: { children: ReactNode }) {
  return (
    <Suspense
      fallback={<p className="text-sm text-stone-500">読み込んでいます</p>}
    >
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
    <section className="rounded-xl border border-stone-200 bg-white p-6 text-sm">
      <p className="mb-4 text-stone-700">
        道標を作ったり見返したりするには、Google でログインしてください。
      </p>
      <SignInButton />
    </section>
  );
}
