import { connection } from "next/server";
import type { ReactNode } from "react";

import { auth } from "@/auth";
import { SignInButton } from "@/components/account";

export async function LoginRequired({ children }: { children: ReactNode }) {
  await connection();
  const session = await auth();
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
