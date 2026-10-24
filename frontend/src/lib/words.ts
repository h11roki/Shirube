const SEGMENTER =
  typeof Intl.Segmenter === "function"
    ? new Intl.Segmenter("ja", { granularity: "word" })
    : undefined;

export type PlateParts = { words: string[]; tail: string };

export function splitWords(text: string): string[] {
  if (!SEGMENTER) {
    return [text];
  }
  const words: string[] = [];
  let lastWordLike = false;
  for (const { segment, isWordLike = false } of SEGMENTER.segment(text)) {
    const startsWord =
      isWordLike && lastWordLike && Array.from(segment).length > 1;
    if (words.length === 0 || startsWord) {
      words.push(segment);
    } else {
      words[words.length - 1] += segment;
    }
    lastWordLike = isWordLike;
  }
  return words;
}

export function plateParts(destination: string): PlateParts {
  const words = splitWords(destination);
  const last = Array.from(words.pop() ?? "");
  const tail = last.pop() ?? "";
  return { words: [...words, last.join("")], tail };
}
