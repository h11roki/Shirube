import type { PlacedCourse } from "@/lib/api/client";
import { slotsLabel } from "@/lib/labels";
import type { RecommendedRelevance } from "@/lib/roadmap";
import { SAMPLE_PLAN } from "@/lib/sample-plan";
import { halfWidthAlphanumerics } from "@/lib/ticket-face";

type RecommendedCourse = PlacedCourse & { relevance: RecommendedRelevance };

const SAMPLE_COURSES = SAMPLE_PLAN.result.semesters
  .flatMap((semester): PlacedCourse[] => semester.courses)
  .filter(
    (course): course is RecommendedCourse => course.relevance !== "fixed",
  );
const SENTENCE = /[^。！？!?]*[。！？!?]+[」』）)】〕］〉》”’]*/g;

export function lastSentence(text: string): string {
  const sentences = text.match(SENTENCE) ?? [];
  const rest = text.slice(sentences.join("").length).trim();
  return rest || sentences.at(-1)?.trim() || text;
}

export const SAMPLE_TICKETS = ["情報処理", "確率統計"].flatMap((name) =>
  SAMPLE_COURSES.filter((course) => course.name === name).map((course) => ({
    ...course,
    name: halfWidthAlphanumerics(course.name),
    reason: lastSentence(course.reason),
    slot: slotsLabel(course),
  })),
);
