import NextAuth from "next-auth";
import Google from "next-auth/providers/google";

import { LOGIN_PATH } from "@/lib/site";

declare module "next-auth" {
  interface Session {
    googleSubject?: string;
  }
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [Google],
  pages: { signIn: LOGIN_PATH, error: LOGIN_PATH },
  session: { strategy: "jwt" },
  callbacks: {
    jwt({ token, account }) {
      if (account?.provider === "google") {
        token.googleSubject = account.providerAccountId;
      }
      return token;
    },
    session({ session, token }) {
      const googleSubject =
        typeof token.googleSubject === "string"
          ? token.googleSubject
          : undefined;
      return { ...session, googleSubject };
    },
  },
});
