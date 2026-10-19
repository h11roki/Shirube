import { signIn, signOut } from "@/auth";
import { currentSession } from "@/lib/session";

export async function Account() {
  const session = await currentSession();
  if (!session?.googleSubject) {
    return <SignInButton />;
  }
  return (
    <form
      className="flex items-center gap-3"
      action={async () => {
        "use server";
        await signOut({ redirectTo: "/" });
      }}
    >
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
