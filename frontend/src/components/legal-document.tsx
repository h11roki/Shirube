import type { ReactNode } from "react";

import { Phrases } from "@/components/phrases";
import { TEXT_LINK } from "@/components/styles";
import { ISSUES_URL } from "@/lib/site";

export function LegalDocument({
  title,
  enactedOn,
  revisedOn,
  children,
}: {
  title: readonly string[];
  enactedOn: string;
  revisedOn?: string;
  children: ReactNode;
}) {
  return (
    <article className="mx-auto grid max-w-2xl gap-8 leading-relaxed [&_h2]:font-serif [&_h2]:text-xl [&_h2]:font-bold [&_section]:grid [&_section]:gap-3 [&_ul]:grid [&_ul]:list-disc [&_ul]:gap-1 [&_ul]:pl-5">
      <header className="grid gap-2">
        <h1 className="font-serif text-3xl font-extrabold">
          <Phrases parts={title} />
        </h1>
        <p className="text-sm text-sub">
          {enactedOn} 制定{revisedOn && `、${revisedOn} 改定`}
        </p>
      </header>
      {children}
    </article>
  );
}

export function ContactSection({ heading }: { heading: string }) {
  return (
    <section>
      <h2>{heading}</h2>
      <p>
        GitHub の Issue(
        <a
          href={ISSUES_URL}
          target="_blank"
          rel="noopener noreferrer"
          className={`${TEXT_LINK} break-all`}
        >
          {ISSUES_URL}
        </a>
        )で受け付けます。
      </p>
    </section>
  );
}
