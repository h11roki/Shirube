export function splitWords(text: string): string[] {
  if (typeof Intl.Segmenter !== "function") {
    return [text];
  }
  return [
    ...new Intl.Segmenter("ja", { granularity: "word" }).segment(text),
  ].map(({ segment }) => segment);
}
