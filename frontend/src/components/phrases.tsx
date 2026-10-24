import { PHRASE_WRAP } from "@/components/styles";

export function Phrases({ parts }: { parts: readonly string[] }) {
  return parts.map((part) => (
    <span key={part} className={`inline-block ${PHRASE_WRAP}`}>
      {part}
    </span>
  ));
}
