"use client";

import { useSyncExternalStore } from "react";

import { DARK_THEME, THEME_STORAGE_KEY } from "@/lib/theme";

function subscribe(onChange: () => void) {
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-theme"],
  });
  return () => observer.disconnect();
}

function isDark() {
  return document.documentElement.dataset.theme === DARK_THEME;
}

export function ThemeToggle() {
  const dark = useSyncExternalStore(subscribe, isDark, () => false);

  function toggle() {
    const root = document.documentElement;
    try {
      if (dark) {
        delete root.dataset.theme;
        localStorage.removeItem(THEME_STORAGE_KEY);
      } else {
        root.dataset.theme = DARK_THEME;
        localStorage.setItem(THEME_STORAGE_KEY, DARK_THEME);
      }
    } catch (error) {
      console.warn("選んだ見た目を覚えられませんでした", error);
    }
  }

  return (
    <button
      type="button"
      aria-pressed={dark}
      onClick={toggle}
      className="flex items-center gap-1 rounded-xs border border-edge py-1.5 pr-2.5 pl-2 text-xs whitespace-nowrap text-sub hover:border-ink hover:text-ink"
    >
      <span
        aria-hidden
        className="relative h-4 w-7 rounded-full bg-edge motion-safe:transition-colors dark:bg-route"
      >
        <span className="absolute top-0.5 left-0.5 size-3 rounded-full bg-paper motion-safe:transition-transform dark:translate-x-3" />
      </span>
      ダークモード
    </button>
  );
}
