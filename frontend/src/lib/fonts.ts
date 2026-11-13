import { Shippori_Mincho, Zen_Kaku_Gothic_New } from "next/font/google";

export const mincho = Shippori_Mincho({
  weight: ["600", "800"],
  display: "swap",
  preload: false,
  variable: "--font-shippori-mincho",
});

export const gothic = Zen_Kaku_Gothic_New({
  weight: ["400", "500", "700"],
  display: "swap",
  preload: false,
  variable: "--font-zen-kaku-gothic-new",
});
