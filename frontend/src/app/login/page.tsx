import type { Metadata } from "next";
import Link from "next/link";

import { LoginRequired } from "@/components/login-required";
import { TEXT_LINK } from "@/components/styles";

export const metadata: Metadata = { title: "ログイン" };

export default function LoginPage() {
  return (
    <LoginRequired>
      <p className="text-sm">
        ログインしています。
        <Link href="/" className={TEXT_LINK}>
          道標を作る
        </Link>
      </p>
    </LoginRequired>
  );
}
