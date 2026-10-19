import type {
  PlacedCourse,
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
  core: "中心",
  foundation: "土台",
};

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
