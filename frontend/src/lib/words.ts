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
const CHARACTERS_WITHOUT_SEGMENTER = /\P{M}\p{M}*|\p{M}+/gu;

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

function charactersOf(text: string): string[] {
  return SEGMENTERS
    ? Array.from(SEGMENTERS.characters.segment(text), ({ segment }) => segment)
    : (text.match(CHARACTERS_WITHOUT_SEGMENTER) ?? []);
}

export function splitTail(words: readonly string[]): {
  words: string[];
  tail: string;
} {
  const last = words.at(-1) ?? "";
  const tail = charactersOf(last).at(-1) ?? "";
  return {
    words: [...words.slice(0, -1), last.slice(0, last.length - tail.length)],
    tail,
  };
}

export function bracketRuns(word: string): { text: string; nowrap: boolean }[] {
  const characters = charactersOf(word);
  const firstLetter = characters.findIndex(
    (character) => !OPENS.test(character),
  );
  const lastLetter = characters.findLastIndex(
    (character) => !CLOSES.test(character),
  );
  const opens = firstLetter === -1 ? characters.length : firstLetter;
  const closes = characters.length - 1 - lastLetter;
  const head = opens > 0 ? opens + 1 : 0;
  const tail = closes > 0 ? closes + 1 : 0;
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
