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

function remember(dark: boolean) {
  try {
    if (dark) {
      localStorage.setItem(THEME_STORAGE_KEY, DARK_THEME);
    } else {
      localStorage.removeItem(THEME_STORAGE_KEY);
    }
  } catch {}
}

export function ThemeToggle() {
  const dark = useSyncExternalStore(subscribe, isDark, () => false);

  function toggle() {
    if (dark) {
      delete document.documentElement.dataset.theme;
    } else {
      document.documentElement.dataset.theme = DARK_THEME;
    }
    remember(!dark);
  }

  return (
    <button
      type="button"
      aria-pressed={dark}
      onClick={toggle}
      className="fixed right-[max(1rem,env(safe-area-inset-right))] bottom-[max(1rem,env(safe-area-inset-bottom))] z-10 flex items-center gap-2 rounded-full border border-line bg-sheet/90 py-1.5 pr-3.5 pl-2 text-xs text-sub shadow-paper backdrop-blur hover:text-ink"
    >
      <span
        aria-hidden
        className={`relative h-4 w-7 rounded-full transition-colors ${dark ? "bg-route" : "bg-line"}`}
      >
        <span
          className={`absolute top-0.5 left-0.5 size-3 rounded-full bg-paper transition-transform ${dark ? "translate-x-3" : ""}`}
        />
      </span>
      ダークモード
    </button>
  );
}
