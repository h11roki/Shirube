import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "shirube",
  description: "なりたい職業から、卒業までの履修の道標を描く",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ja">
      <body>{children}</body>
    </html>
  );
}
