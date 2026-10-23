"use client";

import Link from "next/link";

import { Notice } from "@/components/notice";
import { OUTLINE_BUTTON, STANDALONE_LINK } from "@/components/styles";
import { gothic, mincho } from "@/lib/fonts";
import { THEME_SCRIPT } from "@/lib/theme";

import "./globals.css";

export default function GlobalError() {
  return (
    <html
      lang="ja"
      className={`${mincho.variable} ${gothic.variable}`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="min-h-dvh font-sans text-ink antialiased">
        <main className="mx-auto w-full max-w-5xl px-4 pt-8 pb-16 sm:px-6">
          <Notice title="うまく表示できませんでした">
            <p>
              ページを読み直しても直らなければ、しばらくしてから開いてください。
            </p>
            <div className="flex flex-wrap items-center gap-4">
              <button
                type="button"
                onClick={() => window.location.reload()}
                className={OUTLINE_BUTTON}
              >
                ページを読み直す
              </button>
              <Link href="/" className={STANDALONE_LINK}>
                トップへ
              </Link>
            </div>
          </Notice>
        </main>
      </body>
    </html>
  );
}
