import type { ReactNode } from "react";

export function Kicker({ children }: { children: ReactNode }) {
  return (
    <p className="text-fine text-sub">
      <span aria-hidden>〔</span>
      {children}
      <span aria-hidden>〕</span>
    </p>
  );
}
