import type { ReactNode } from "react";

export default function LegalLayout({ children }: { children: ReactNode }) {
  return (
    <article className="mx-auto grid max-w-2xl gap-8 leading-relaxed [&_a]:break-all [&_a]:text-route [&_a]:underline [&_a]:underline-offset-4 [&_h1]:font-serif [&_h1]:text-3xl [&_h1]:font-extrabold [&_h2]:font-serif [&_h2]:text-xl [&_h2]:font-bold [&_section]:grid [&_section]:gap-3 [&_ul]:grid [&_ul]:list-disc [&_ul]:gap-1 [&_ul]:pl-5">
      {children}
    </article>
  );
}
