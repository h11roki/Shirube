"use client";

import type { CSSProperties, ReactNode } from "react";
import { useState } from "react";

export function Tilt({
  className,
  children,
}: {
  className: string;
  children: ReactNode;
}) {
  const [angle, setAngle] = useState<CSSProperties>();
  return (
    <div
      style={angle}
      onPointerMove={(event) => {
        if (
          event.pointerType !== "mouse" ||
          matchMedia("(prefers-reduced-motion: reduce)").matches
        ) {
          return;
        }
        const box = event.currentTarget.getBoundingClientRect();
        setAngle({
          "--tilt-x": `${(0.5 - (event.clientY - box.top) / box.height) * 8}deg`,
          "--tilt-y": `${((event.clientX - box.left) / box.width - 0.5) * 10}deg`,
        } as CSSProperties);
      }}
      onPointerLeave={() => setAngle(undefined)}
      className={className}
    >
      {children}
    </div>
  );
}
