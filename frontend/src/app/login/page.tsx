import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { LoginRequired } from "@/components/login-required";

export const metadata: Metadata = { title: "ログイン" };

export default function LoginPage() {
  return (
    <LoginRequired>
      <BackToTop />
    </LoginRequired>
  );
}

function BackToTop(): never {
  redirect("/");
}
