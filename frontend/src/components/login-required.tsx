import type { ReactNode } from "react";

import { SignInButton } from "@/components/account";
import { currentSession } from "@/lib/session";

export async function LoginRequired({ children }: { children: ReactNode }) {
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
