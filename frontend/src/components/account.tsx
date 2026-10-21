import Link from "next/link";

import { signIn } from "@/auth";
import { TEXT_LINK } from "@/components/styles";
import { currentSession } from "@/lib/session";
import { signOutToTop } from "@/lib/sign-out";

export async function Account() {
  const session = await currentSession();
  if (!session?.googleSubject) {
    return null;
  }
  return (
    <form className="flex items-center gap-3" action={signOutToTop}>
      <span className="hidden sm:inline">
        {session.user?.name ?? "Google のアカウント"}
      </span>
      <button type="submit" className="hover:text-ink">
        ログアウト
      </button>
    </form>
  );
}

export function SignInButton() {
  return (
    <form
      action={async () => {
        "use server";
        await signIn("google");
      }}
      className="grid justify-items-start gap-2"
    >
      <button
        type="submit"
        className="rounded-full bg-pillar px-4 py-1.5 font-medium text-paper hover:opacity-90"
      >
        Google でログイン
      </button>
      <p className="text-xs text-sub">
        ログインすると、
        <Link href="/terms" className={TEXT_LINK}>
          利用規約
        </Link>
        と
        <Link href="/privacy" className={TEXT_LINK}>
          プライバシーポリシー
        </Link>
        に同意したことになります。
      </p>
    </form>
  );
}
