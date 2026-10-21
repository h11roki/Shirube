import Link from "next/link";

import { ISSUES_URL, OPERATOR, REPOSITORY_URL } from "@/lib/site";

export function SiteFooter() {
  return (
    <footer className="border-t border-line">
      <div className="mx-auto grid max-w-5xl gap-3 px-4 pt-8 pb-20 text-xs text-sub sm:px-6">
        <p>
          shirube は、立命館大学とは関係のない個人({OPERATOR}
          )が作った非公式のアプリです。授業の情報は、大学の公開シラバスと時間割表によります。
        </p>
        <nav className="flex flex-wrap gap-x-5 gap-y-1">
          <Link href="/terms" className="hover:text-ink">
            利用規約
          </Link>
          <Link href="/privacy" className="hover:text-ink">
            プライバシーポリシー
          </Link>
          <a href={REPOSITORY_URL} className="hover:text-ink">
            GitHub
          </a>
          <a href={ISSUES_URL} className="hover:text-ink">
            問い合わせ(Issue)
          </a>
        </nav>
      </div>
    </footer>
  );
}
