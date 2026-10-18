import { connection } from "next/server";
import { Suspense } from "react";

import { auth, signIn, signOut } from "@/auth";

async function Account() {
  await connection();
  const session = await auth();
  if (!session?.user) {
    return (
      <form
        action={async () => {
          "use server";
          await signIn("google");
        }}
      >
        <button type="submit">Google でログイン</button>
      </form>
    );
  }
  return (
    <form
      action={async () => {
        "use server";
        await signOut();
      }}
    >
      <p>{session.user.name} でログインしています</p>
      <button type="submit">ログアウト</button>
    </form>
  );
}

export default function Home() {
  return (
    <main>
      <h1>shirube</h1>
      <Suspense>
        <Account />
      </Suspense>
    </main>
  );
}
