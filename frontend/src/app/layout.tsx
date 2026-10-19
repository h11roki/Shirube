import type { Metadata } from "next";
import { Shippori_Mincho, Zen_Kaku_Gothic_New } from "next/font/google";

import { SiteHeader } from "@/components/site-header";
import { ThemeToggle } from "@/components/theme-toggle";
import { THEME_SCRIPT } from "@/lib/theme";

import "./globals.css";

const mincho = Shippori_Mincho({
  weight: ["600", "800"],
  subsets: ["latin"],
  display: "swap",
  variable: "--font-shippori-mincho",
});

const gothic = Zen_Kaku_Gothic_New({
  weight: ["400", "500", "700"],
  subsets: ["latin"],
  display: "swap",
  variable: "--font-zen-kaku-gothic-new",
});

export const metadata: Metadata = {
  title: { default: "shirube", template: "%s | shirube" },
  description: "なりたい職業から、卒業までの履修の道標を描く",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="ja"
      className={`${mincho.variable} ${gothic.variable} motion-safe:scroll-smooth`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="min-h-dvh font-sans text-ink antialiased">
        <SiteHeader />
        <main className="mx-auto w-full max-w-5xl px-4 pt-8 pb-24 sm:px-6">
          {children}
        </main>
        <ThemeToggle />
      </body>
    </html>
  );
}
