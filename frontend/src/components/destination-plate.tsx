export function DestinationPlate({ destination }: { destination: string }) {
  return (
    <p
      aria-hidden
      className="inline-block justify-self-start rounded-md border border-line bg-plate px-5 py-2 text-plate-ink shadow-paper"
    >
      <span className="font-serif text-2xl leading-snug font-extrabold tracking-wide text-balance sm:text-3xl">
        {destination}
        <span className="ml-1.5 text-pillar">行</span>
      </span>
    </p>
  );
}
