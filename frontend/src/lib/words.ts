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
const OPENS_AT_START = /^[\p{Ps}\p{Pi}]/u;

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

export function wordsByText(
  texts: readonly string[],
): Record<string, string[]> {
  return Object.fromEntries(texts.map((text) => [text, wordsOf(text)]));
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

export function bracketRuns(word: string): { text: string; nowrap: boolean }[] {
  const characters = SEGMENTERS
    ? Array.from(SEGMENTERS.characters.segment(word), ({ segment }) => segment)
    : Array.from(word);
  const head = OPENS_AT_START.test(word) ? 2 : 0;
  const tail = CLOSES.test(word) ? 2 : 0;
  if (head + tail >= characters.length) {
    return [{ text: word, nowrap: head + tail > 0 }];
  }
  return [
    { text: characters.slice(0, head).join(""), nowrap: true },
    {
      text: characters.slice(head, characters.length - tail).join(""),
      nowrap: false,
    },
    { text: characters.slice(characters.length - tail).join(""), nowrap: true },
  ].filter((run) => run.text !== "");
}
