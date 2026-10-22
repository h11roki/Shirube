"use client";

import { OUTLINE_BUTTON } from "@/components/styles";
import { gothic, mincho } from "@/lib/fonts";
import { THEME_SCRIPT } from "@/lib/theme";

import "./globals.css";

export default function GlobalError({ reset }: { reset: () => void }) {
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
          <section
            role="alert"
            className="mx-auto grid max-w-xl justify-items-start gap-3 rounded-lg border border-danger/30 bg-danger-soft p-6 text-sm"
          >
            <h1 className="font-serif text-xl font-bold text-danger">
              うまく表示できませんでした
            </h1>
            <p>
              もう一度試しても直らなければ、しばらくしてから開いてください。
            </p>
            <button type="button" onClick={reset} className={OUTLINE_BUTTON}>
              もう一度試す
            </button>
          </section>
        </main>
      </body>
    </html>
  );
}
