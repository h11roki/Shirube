import { signIn } from "@/auth";
import { currentSession } from "@/lib/session";
import { signOutToTop } from "@/lib/sign-out";

export async function Account() {
  const session = await currentSession();
  if (!session?.googleSubject) {
    return <SignInButton />;
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
    >
      <button
        type="submit"
        className="rounded-full bg-pillar px-4 py-1.5 font-medium text-paper hover:opacity-90"
      >
        Google でログイン
      </button>
    </form>
  );
}
