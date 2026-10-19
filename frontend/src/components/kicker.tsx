import type { ReactNode } from "react";

export function Kicker({ children }: { children: ReactNode }) {
  return (
    <p className="text-xs font-bold tracking-[0.28em] text-pillar">
      {children}
    </p>
  );
}
