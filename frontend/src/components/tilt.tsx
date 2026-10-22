"use client";

import type { CSSProperties, ReactNode } from "react";
import { useState } from "react";

const SWING_DEGREES = { x: 8, y: 10 };
const STILL = "(hover: none), (prefers-reduced-motion: reduce)";

export function Tilt({
  className,
  children,
}: {
  className: string;
  children: ReactNode;
}) {
  const [tilt, setTilt] = useState<CSSProperties>();
  return (
    <div
      style={tilt}
      onPointerMove={(event) => {
        if (event.pointerType !== "mouse" || matchMedia(STILL).matches) {
          return;
        }
        const box = event.currentTarget.getBoundingClientRect();
        setTilt({
          "--tilt-x": `${(0.5 - (event.clientY - box.top) / box.height) * SWING_DEGREES.x}deg`,
          "--tilt-y": `${((event.clientX - box.left) / box.width - 0.5) * SWING_DEGREES.y}deg`,
        } as CSSProperties);
      }}
      onPointerLeave={() => setTilt(undefined)}
      className={className}
    >
      {children}
    </div>
  );
}
