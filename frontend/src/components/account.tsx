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
      <span className="hidden text-stone-600 sm:inline">
        {session.user?.name ?? "Google のアカウント"}
      </span>
      <button
        type="submit"
        className="rounded-md px-2 py-1 text-stone-600 hover:bg-stone-100 hover:text-stone-900"
      >
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
        className="rounded-md bg-teal-700 px-3 py-1.5 font-medium text-white hover:bg-teal-800"
      >
        Google でログイン
      </button>
    </form>
  );
}
