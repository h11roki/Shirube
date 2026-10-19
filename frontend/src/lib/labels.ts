import type {
  Course,
  PlacedCourse,
  PlanStage,
  PlanStatus,
  Relevance,
  Term,
  Weekday,
} from "@/lib/api/client";

export const STATUS_LABELS: Record<PlanStatus, string> = {
  pending: "待ち",
  running: "作成中",
  succeeded: "完了",
  failed: "失敗",
};

export const RELEVANCE_LABELS: Record<Relevance, string> = {
  core: "柱",
  foundation: "礎",
};

export const STAGE_LABELS: Record<PlanStage, string> = {
  analyzing: "目的地を地図に書き込んでいます",
  searching: "道を探しています",
  selecting: "通る授業を選んでいます",
  placing: "道標を立てています",
};

export const WAITING_LABEL = "順番を待っています";

export const TERM_LABELS: Record<Term, string> = {
  spring: "春学期",
  autumn: "秋学期",
};

export const WEEKDAY_LABELS: Record<Weekday, string> = {
  mon: "月",
  tue: "火",
  wed: "水",
  thu: "木",
  fri: "金",
  sat: "土",
  sun: "日",
};

export function semesterLabel(grade: number, term: Term): string {
  return `${grade} 回生 ${TERM_LABELS[term]}`;
}

export function roleLabel(
  course: Pick<Course, "relevance" | "prerequisite_for">,
): string {
  if (course.relevance === "foundation" && course.prerequisite_for) {
    return `${course.prerequisite_for}の${RELEVANCE_LABELS.foundation}`;
  }
  return RELEVANCE_LABELS[course.relevance];
}

export function slotsLabel(course: PlacedCourse): string {
  return (
    course.slots
      .map((slot) => `${WEEKDAY_LABELS[slot.weekday]}${slot.period}`)
      .join("・") || "コマなし"
  );
}

export function classLabel(classCode: string): string {
  return classCode || "記号なし";
}
