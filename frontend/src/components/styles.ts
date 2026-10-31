export const TEXT_LINK = "text-route underline underline-offset-4";

const TARGET = "inline-flex min-h-6 items-center";

export const STANDALONE_LINK = `${TARGET} ${TEXT_LINK}`;

export const NAV_LINK = `${TARGET} hover:text-ink`;

export const OUTLINED = "rounded-xs border border-edge";

export const OUTLINE_BUTTON = `${OUTLINED} bg-sheet px-4 py-1.5 text-ink hover:border-ink`;

export const SMALL_BUTTON = `${OUTLINED} px-3 py-1 text-xs text-sub hover:border-ink hover:text-ink disabled:opacity-50`;

const SOLID_BUTTON = "rounded-xs text-paper hover:opacity-90";

export const PRIMARY_BUTTON = `${SOLID_BUTTON} bg-ink`;

export const DANGER_BUTTON = `${SOLID_BUTTON} bg-danger`;

export function tabClass(current: boolean): string {
  return `pt-1 ${current ? "border-b-[3px] border-route pb-1.5 text-ink" : "border-b border-line pb-2 text-sub hover:text-ink"}`;
}

export const PLATE = "border border-line bg-plate text-plate-ink";

export const DESTINATION_TEXT =
  "text-[clamp(1.125rem,5.9vw,1.5rem)] leading-snug";

export const TICKET_NOTCH_SHAPE =
  "before:absolute before:size-4 before:rounded-full before:border before:border-line before:bg-paper after:absolute after:size-4 after:rounded-full after:border after:border-line after:bg-paper";

export const TICKET_NOTCH = `${TICKET_NOTCH_SHAPE} before:-top-2 before:-left-[calc(0.5rem+1px)] before:[clip-path:inset(50%_0_0_0)] after:-bottom-2 after:-left-[calc(0.5rem+1px)] after:[clip-path:inset(0_0_50%_0)]`;

export const COURSE_TICKET_NOTCH = `${TICKET_NOTCH} max-sm:before:-top-[calc(0.5rem+1px)] max-sm:before:-left-2 max-sm:before:[clip-path:inset(0_0_0_50%)] max-sm:after:-top-[calc(0.5rem+1px)] max-sm:after:-right-2 max-sm:after:bottom-auto max-sm:after:left-auto max-sm:after:[clip-path:inset(0_50%_0_0)]`;

export const TICKET_STAMP =
  "absolute top-2.5 grid rotate-[-12deg] place-items-center rounded-full border-[2.5px] border-pillar font-serif font-extrabold text-pillar";
