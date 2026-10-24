export const TEXT_LINK = "text-route underline underline-offset-4";

const TARGET = "inline-flex min-h-6 items-center";

export const STANDALONE_LINK = `${TARGET} ${TEXT_LINK}`;

export const NAV_LINK = `${TARGET} hover:text-ink`;

export const OUTLINE_BUTTON =
  "rounded-full border border-edge bg-sheet px-4 py-1.5 text-ink hover:border-ink";

export const SMALL_BUTTON =
  "rounded-full border border-edge px-3 py-1 text-xs text-sub hover:border-ink hover:text-ink disabled:opacity-50";

export const PHRASE_WRAP = "[overflow-wrap:anywhere] [word-break:auto-phrase]";

export const TICKET_NOTCH =
  "before:absolute before:-top-2 before:-left-[9px] before:size-4 before:rounded-full before:border before:border-line before:bg-paper before:[clip-path:inset(50%_0_0_0)] after:absolute after:-bottom-2 after:-left-[9px] after:size-4 after:rounded-full after:border after:border-line after:bg-paper after:[clip-path:inset(0_0_50%_0)]";

export const TICKET_STAMP =
  "absolute top-2.5 grid rotate-[-12deg] place-items-center rounded-full border-[2.5px] border-pillar font-serif font-extrabold text-pillar";
