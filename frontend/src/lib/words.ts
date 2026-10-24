const SEGMENTERS =
  typeof Intl.Segmenter === "function"
    ? {
        words: new Intl.Segmenter("ja", { granularity: "word" }),
        characters: new Intl.Segmenter("ja", { granularity: "grapheme" }),
      }
    : undefined;

const OPENS = /[\p{Ps}\p{Pi}]$/u;
const PARTICLES = /^[のとやをにへでがはも]$/u;

type Previous = "word" | "letter" | "particle" | "open" | "mark";

export type DestinationParts = { words: string[]; tail: string };

function splitWords(
  text: string,
  segmenters: NonNullable<typeof SEGMENTERS>,
): string[] {
  const words: string[] = [];
  let previous: Previous | undefined;
  for (const { segment, isWordLike = false } of segmenters.words.segment(
    text,
  )) {
    const letter =
      isWordLike &&
      segmenters.characters.segment(segment).containing(0)?.segment === segment;
    const particle = isWordLike && PARTICLES.test(segment);
    const opening = !isWordLike && OPENS.test(segment);
    const breaksBefore = isWordLike
      ? !particle &&
        ((previous === "word" && !letter) ||
          previous === "particle" ||
          previous === "mark")
      : opening && previous !== "open";
    if (previous === undefined || breaksBefore) {
      words.push(segment);
    } else {
      words[words.length - 1] += segment;
    }
    if (isWordLike) {
      previous = particle ? "particle" : letter ? "letter" : "word";
    } else {
      previous = opening ? "open" : "mark";
    }
  }
  return words;
}

export function wordsOf(text: string): string[] {
  return SEGMENTERS ? splitWords(text, SEGMENTERS) : [text];
}

export function destinationParts(destination: string): DestinationParts {
  const words = wordsOf(destination);
  const last = words.pop() ?? "";
  const tail = SEGMENTERS
    ? (SEGMENTERS.characters.segment(last).containing(last.length - 1)
        ?.segment ?? "")
    : (Array.from(last).at(-1) ?? "");
  return { words: [...words, last.slice(0, last.length - tail.length)], tail };
}

export function wholeWords({ words, tail }: DestinationParts): string[] {
  return words.map((word, index) =>
    index === words.length - 1 ? `${word}${tail}` : word,
  );
}
