import { SAMPLE_PLAN } from "@/lib/sample-plan";

const SAMPLE_COURSES = SAMPLE_PLAN.result.semesters.flatMap(
  (semester) => semester.courses,
);

export const SAMPLE_TICKETS = ["電子情報基礎数学", "ＡＩ・機械学習"].flatMap(
  (name) =>
    SAMPLE_COURSES.filter((course) => course.name === name).map((course) => ({
      ...course,
      name: course.name.normalize("NFKC"),
    })),
);

export function lastSentence(text: string): string {
  return (
    text
      .split(/(?<=。)/)
      .filter((sentence) => sentence.trim() !== "")
      .at(-1) ?? text
  );
}
