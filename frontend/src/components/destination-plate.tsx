export function DestinationPlate({ destination }: { destination: string }) {
  return (
    <p
      aria-hidden
      className="inline-grid justify-items-start justify-self-start rounded-md border border-line bg-plate px-5 pt-1.5 pb-2.5 text-plate-ink shadow-paper"
    >
      <span className="text-[10.5px] tracking-[0.3em] opacity-70">
        しるべ線 ・ 各駅停車
      </span>
      <span className="font-serif text-2xl leading-snug font-extrabold tracking-wide text-balance sm:text-3xl">
        {destination}
        <span className="ml-1.5 text-pillar">行</span>
      </span>
    </p>
  );
}
