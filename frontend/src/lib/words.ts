const SEGMENTERS =
  typeof Intl.Segmenter === "function"
    ? {
        words: new Intl.Segmenter("ja", { granularity: "word" }),
        characters: new Intl.Segmenter("ja", { granularity: "grapheme" }),
      }
    : undefined;

const OPENS = /[\p{Ps}\p{Pi}]$/u;

type Previous = "word" | "letter" | "open" | "mark";

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
    const breaksBefore =
      isWordLike && ((previous === "word" && !letter) || previous === "mark");
    if (previous === undefined || breaksBefore) {
      words.push(segment);
    } else {
      words[words.length - 1] += segment;
    }
    if (isWordLike) {
      previous = letter ? "letter" : "word";
    } else {
      previous = OPENS.test(segment) ? "open" : "mark";
    }
  }
  return words;
}

export function plateParts(destination: string): {
  words: string[];
  tail: string;
} {
  if (!SEGMENTERS) {
    const characters = Array.from(destination);
    const tail = characters.pop() ?? "";
    return { words: [characters.join("")], tail };
  }
  const words = splitWords(destination, SEGMENTERS);
  const last = words.pop() ?? "";
  const tail =
    SEGMENTERS.characters.segment(last).containing(last.length - 1)?.segment ??
    "";
  return { words: [...words, last.slice(0, last.length - tail.length)], tail };
}
