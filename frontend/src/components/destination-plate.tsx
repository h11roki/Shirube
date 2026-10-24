import { DestinationName } from "@/components/destination-name";
import { DESTINATION_TEXT } from "@/components/styles";

export function DestinationPlate({ words }: { words: readonly string[] }) {
  return (
    <p
      aria-hidden
      className="inline-block justify-self-start rounded-md border border-line bg-plate px-5 py-2 text-plate-ink shadow-paper"
    >
      <span
        className={`block font-serif font-extrabold tracking-wide text-balance sm:text-3xl ${DESTINATION_TEXT}`}
      >
        <DestinationName words={words}>
          <span className="ml-1.5 text-plate-accent">行</span>
        </DestinationName>
      </span>
    </p>
  );
}
