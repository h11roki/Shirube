export function GraduationStamp({ station }: { station: string }) {
  return (
    <span
      aria-hidden
      className="relative grid size-24 shrink-0 rotate-[-8deg] place-items-center rounded-full border-[3px] border-pillar text-center leading-tight text-pillar before:absolute before:inset-1.5 before:rounded-full before:border-[1.5px] before:border-dashed before:border-pillar motion-safe:animate-press motion-safe:[animation-delay:var(--arrive,0ms)]"
    >
      <span className="grid">
        <span className="text-[9px] tracking-[0.2em]">しるべ線</span>
        <span className="font-serif text-2xl font-extrabold tracking-[0.1em]">
          卒業
        </span>
        <span className="text-[9.5px] tracking-[0.1em] tabular-nums">
          {station}
        </span>
      </span>
    </span>
  );
}
