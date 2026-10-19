export function Signpost({
  from,
  className,
}: {
  from: string;
  className?: string;
}) {
  return (
    <svg viewBox="0 0 96 116" aria-hidden className={className}>
      <rect x="44" y="16" width="8" height="98" className="fill-ink/85" />
      <path d="M14 20h62l12 11-12 11H14z" className="fill-pillar" />
      <path d="M82 52H22L8 63l14 11h60z" className="fill-route" />
      <text
        x="45"
        y="35"
        textAnchor="middle"
        className="fill-paper font-serif text-[11px] font-bold"
      >
        卒業
      </text>
      <text
        x="51"
        y="67"
        textAnchor="middle"
        className="fill-paper font-serif text-[11px] font-bold"
      >
        {from}
      </text>
    </svg>
  );
}
