import { DestinationName } from "@/components/destination-name";
import { DESTINATION_TEXT, PLATE } from "@/components/styles";
import type { Destination } from "@/lib/words";

export function DestinationPlate({
  destination,
  arriving = false,
}: {
  destination: Destination;
  arriving?: boolean;
}) {
  return (
    <p
      aria-hidden
      className={`inline-block justify-self-start px-5 py-2 ${PLATE}`}
    >
      <span
        className={`block font-serif font-extrabold tracking-wide text-balance sm:text-3xl ${DESTINATION_TEXT} ${arriving ? "motion-safe:animate-roll-in" : ""}`}
      >
        <DestinationName words={destination.words}>
          <span className="ml-1.5 text-plate-accent">行</span>
        </DestinationName>
      </span>
    </p>
  );
}
