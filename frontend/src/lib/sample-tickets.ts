import { slotsLabel } from "@/lib/labels";
import { SAMPLE_PLAN } from "@/lib/sample-plan";
import { halfWidthAlphanumerics } from "@/lib/ticket-face";

const SAMPLE_COURSES = SAMPLE_PLAN.result.semesters.flatMap(
  (semester) => semester.courses,
);
const SENTENCE = /[^。！？!?]*[。！？!?]+[」』）)】〕］〉》”’]*/g;

export function lastSentence(text: string): string {
  const sentences = text.match(SENTENCE) ?? [];
  const rest = text.slice(sentences.join("").length).trim();
  return rest || sentences.at(-1)?.trim() || text;
}

export const SAMPLE_TICKETS = ["電子情報基礎数学", "ＡＩ・機械学習"].flatMap(
  (name) =>
    SAMPLE_COURSES.filter((course) => course.name === name).map((course) => ({
      ...course,
      name: halfWidthAlphanumerics(course.name),
      reason: lastSentence(course.reason),
      slot: slotsLabel(course),
    })),
);
