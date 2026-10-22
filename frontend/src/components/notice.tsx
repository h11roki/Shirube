import type { ReactNode } from "react";

export function Notice({
  title,
  heading: Heading = "h1",
  children,
}: {
  title: string;
  heading?: "h1" | "h2";
  children: ReactNode;
}) {
  return (
    <section
      role="alert"
      className="mx-auto grid max-w-xl justify-items-start gap-3 rounded-lg border border-danger/30 bg-danger-soft p-6 text-sm"
    >
      <Heading className="font-serif text-xl font-bold text-danger">
        {title}
      </Heading>
      {children}
    </section>
  );
}
