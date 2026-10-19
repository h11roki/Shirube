import type { Metadata } from "next";

import { SiteHeader } from "@/components/site-header";

import "./globals.css";

export const metadata: Metadata = {
  title: { default: "shirube", template: "%s | shirube" },
  description: "なりたい職業から、卒業までの履修の道標を描く",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ja">
      <body className="min-h-dvh bg-stone-50 text-stone-900 antialiased">
        <SiteHeader />
        <main className="mx-auto w-full max-w-4xl px-4 py-8 sm:px-6">
          {children}
        </main>
      </body>
    </html>
  );
}
