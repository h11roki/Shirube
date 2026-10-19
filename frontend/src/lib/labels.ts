import type {
  Course,
  PlacedCourse,
  PlanStage,
  PlanStatus,
  Relevance,
  Term,
  Weekday,
} from "@/lib/api/client";
import type { ResultView } from "@/lib/result-view";
import type { Transfer, TransferOrder } from "@/lib/roadmap";

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

export const DEPARTMENT_NAME = "電子情報工学科";

export const EMPTY_SEMESTER_LABEL = "この学期に置いた授業はありません。";

export const CONTINUING_LABEL = "春学期からの続き";

export const RESULT_VIEW_LABELS: Record<ResultView, string> = {
  route: "道のり",
  timetable: "時間割帳",
};

export const TERM_LABELS: Record<Term, string> = {
  spring: "春学期",
  autumn: "秋学期",
};

const TERM_READINGS: Record<Term, string> = {
  spring: "はるがっき",
  autumn: "あきがっき",
};

const GRADE_READINGS: Record<number, string> = {
  1: "いっかいせい",
  2: "にかいせい",
  3: "さんかいせい",
  4: "よんかいせい",
};

const STATION_PREFIX = "SH";

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

const TERM_SHORT_LABELS: Record<Term, string> = {
  spring: "春",
  autumn: "秋",
};

export function semesterShortLabel(grade: number, term: Term): string {
  return `${grade}回生 ${TERM_SHORT_LABELS[term]}`;
}

export function semesterReading(grade: number, term: Term): string {
  return `${GRADE_READINGS[grade] ?? `${grade} かいせい`} ${TERM_READINGS[term]}`;
}

export function stationLabel(index: number): string {
  return `${STATION_PREFIX}${String(index + 1).padStart(2, "0")}`;
}

export function goalStationLabel(semesterCount: number): string {
  return stationLabel(semesterCount);
}

export function transferLabel(
  transfer: Pick<Transfer, "pillar" | "station" | "semester">,
): string {
  return `乗換 → ${transfer.pillar}(${stationLabel(transfer.station)} ${semesterLabel(transfer.semester.grade, transfer.semester.term)})`;
}

const NOT_EARLIER = `${RELEVANCE_LABELS.core}より前の学期には置けませんでした`;

export const TRANSFER_WARNINGS: Record<TransferOrder, string | null> = {
  before: null,
  same: `${RELEVANCE_LABELS.core}と同じ学期です。${NOT_EARLIER}`,
  after: `${RELEVANCE_LABELS.core}より後の学期です。${NOT_EARLIER}`,
};

export type TakenChange = "mark" | "unmark";

const TAKEN_VERBS: Record<TakenChange, string> = {
  mark: "外して",
  unmark: "戻して",
};

export function answeredLabel(name: string, change: TakenChange): string {
  return `${name}を${TAKEN_VERBS[change]}置き直しました`;
}

export function markTakenLabel(name: string): string {
  return `${name}はもう取った`;
}

export function unmarkTakenLabel(name: string): string {
  return `${name}を道標に戻す`;
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
