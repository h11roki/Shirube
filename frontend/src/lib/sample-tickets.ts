import { SAMPLE_PLAN } from "@/lib/sample-plan";

const SAMPLE_COURSES = SAMPLE_PLAN.result.semesters.flatMap(
  (semester) => semester.courses,
);
const SENTENCE = /[^。！？!?]*[。！？!?]+[」』）)】〕］〉》”’]*/g;
const FULL_WIDTH_ALPHANUMERIC = /[Ａ-Ｚａ-ｚ０-９]/g;
const FULL_WIDTH_OFFSET = 0xfee0;

export function lastSentence(text: string): string {
  const sentences = text.match(SENTENCE) ?? [];
  const rest = text.slice(sentences.join("").length).trim();
  return rest || sentences.at(-1)?.trim() || text;
}

export function halfWidthAlphanumerics(text: string): string {
  return text.replace(FULL_WIDTH_ALPHANUMERIC, (letter) =>
    String.fromCharCode(letter.charCodeAt(0) - FULL_WIDTH_OFFSET),
  );
}

export const SAMPLE_TICKETS = ["電子情報基礎数学", "ＡＩ・機械学習"].flatMap(
  (name) =>
    SAMPLE_COURSES.filter((course) => course.name === name).map((course) => ({
      ...course,
      name: halfWidthAlphanumerics(course.name),
      reason: lastSentence(course.reason),
    })),
);
