const SEGMENTERS =
  typeof Intl.Segmenter === "function"
    ? {
        words: new Intl.Segmenter("ja", { granularity: "word" }),
        characters: new Intl.Segmenter("ja", { granularity: "grapheme" }),
      }
    : undefined;

const OPENS = /[\p{Ps}\p{Pi}]$/u;
const CLOSES = /[\p{Pe}\p{Pf}]$/u;
const PARTICLES = /^[のとやをにへでがはも]$/u;

type Previous = "word" | "letter" | "particle" | "open" | "close" | "mark";

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
        (((previous === "word" || previous === "close") && !letter) ||
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
      previous = opening ? "open" : CLOSES.test(segment) ? "close" : "mark";
    }
  }
  return words;
}

export function wordsOf(text: string): string[] {
  return SEGMENTERS ? splitWords(text, SEGMENTERS) : [text];
}

export type Destination = { name: string; words: string[] };

export function destinationOf(name: string): Destination {
  return { name, words: wordsOf(name) };
}

export function splitTail(words: readonly string[]): {
  words: string[];
  tail: string;
} {
  const last = words.at(-1) ?? "";
  const tail = SEGMENTERS
    ? (SEGMENTERS.characters.segment(last).containing(last.length - 1)
        ?.segment ?? "")
    : (Array.from(last).at(-1) ?? "");
  return {
    words: [...words.slice(0, -1), last.slice(0, last.length - tail.length)],
    tail,
  };
}
