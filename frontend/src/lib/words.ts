const WORDS =
  typeof Intl.Segmenter === "function"
    ? new Intl.Segmenter("ja", { granularity: "word" })
    : undefined;

const GRAPHEMES =
  typeof Intl.Segmenter === "function"
    ? new Intl.Segmenter("ja", { granularity: "grapheme" })
    : undefined;

function graphemes(text: string): string[] {
  return GRAPHEMES
    ? Array.from(GRAPHEMES.segment(text), ({ segment }) => segment)
    : Array.from(text);
}

export function splitWords(text: string): string[] {
  if (!WORDS) {
    return [text];
  }
  const words: string[] = [];
  let lastWordLike = false;
  for (const { segment, isWordLike = false } of WORDS.segment(text)) {
    const startsWord =
      isWordLike && lastWordLike && graphemes(segment).length > 1;
    if (words.length === 0 || startsWord) {
      words.push(segment);
    } else {
      words[words.length - 1] += segment;
    }
    lastWordLike = isWordLike;
  }
  return words;
}

export function plateParts(destination: string): {
  words: string[];
  tail: string;
} {
  const words = splitWords(destination);
  const last = words.pop() ?? "";
  const tail = graphemes(last).at(-1) ?? "";
  return { words: [...words, last.slice(0, last.length - tail.length)], tail };
}
