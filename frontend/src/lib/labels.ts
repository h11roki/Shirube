import type {
  Course,
  PlacedCourse,
  Plan,
  PlanStage,
  PlanStatus,
  Relevance,
  Term,
  Weekday,
} from "@/lib/api/client";
import type { ResultView } from "@/lib/result-view";
import type { Transfer } from "@/lib/roadmap";

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

const PLAN_TITLE_PREFIXES: Record<Exclude<PlanStatus, "succeeded">, string> = {
  pending: "作成中: ",
  running: "作成中: ",
  failed: "作れませんでした: ",
};

type PlanState = Pick<Plan, "status" | "result">;

function completedInView(plan: PlanState, sawProgress: boolean): boolean {
  return plan.status === "succeeded" && plan.result !== null && sawProgress;
}

export function planTabTitle(
  base: string,
  plan: PlanState,
  sawProgress: boolean,
): string {
  if (plan.status !== "succeeded") {
    return `${PLAN_TITLE_PREFIXES[plan.status]}${base}`;
  }
  return completedInView(plan, sawProgress) ? `できました: ${base}` : base;
}

export function completionNotice(
  plan: PlanState,
  sawProgress: boolean,
): string {
  return completedInView(plan, sawProgress) ? "道標ができました" : "";
}

export const DEPARTMENT_NAME = "電子情報工学科";

export const EMPTY_SEMESTER_LABEL = "この学期に置いた授業はありません。";

export const NO_LESSONS_LABEL = "授業なし";

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

export function routeEndLabel(
  destination: string,
  shown: number,
  total: number,
): string {
  return shown < total ? `${destination}へ続きます` : `${destination}へ`;
}

export function transferLabel(
  transfer: Pick<Transfer, "pillar" | "station" | "semester">,
): string {
  return `乗換 → ${transfer.pillar}(${stationLabel(transfer.station)} ${semesterLabel(transfer.semester.grade, transfer.semester.term)})`;
}

export type TakenChange = "mark" | "unmark";

const TAKEN_VERBS: Record<TakenChange, string> = {
  mark: "外して",
  unmark: "戻して",
};

export function answeredLabel(name: string, change: TakenChange): string {
  return `${name}を${TAKEN_VERBS[change]}置き直しました`;
}

export function failedAnswerLabel(
  answering: string,
  reloading: string | null,
): string {
  return reloading
    ? `${answering}(道標も読み直せませんでした: ${reloading})`
    : answering;
}

export function markTakenLabel(name: string): string {
  return `${name}はもう取った`;
}

export function forgetTakenLabel(name: string): string {
  return `${name}を取り消す`;
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

export const PLAN_CAUTION =
  "非公式の参考です。必修、卒業要件、履修の前提は見ていません。授業は AI が選ぶので、誤りや作るたびの違いがあります。履修登録の前に、大学の履修要項とシラバスで確かめてください。";

export function sampleLabel(occupation: string): string {
  return `見本 ── ${occupation}`;
}

export function syllabusLinkLabel(name: string): string {
  return `${name}のシラバスを新しいタブで開く`;
}

export function sourceNote(year: number): string {
  return `授業の情報は、立命館大学の ${year} 年度のシラバスと時間割表によります。来年度以降の学期も、${year} 年度の時間割で組んでいます。`;
}

export const RETRY_LABEL = "読み直す";

export const SIGN_IN_AGAIN_LABEL = "ログインし直す";

export const DELETE_PLAN_LABEL = "この道標を消す";

export const DELETE_ROW_LABEL = "消す";

export const CONFIRM_DELETE_LABEL = "本当に消す";

export const CANCEL_LABEL = "やめる";

export const DELETE_PLAN_NOTE =
  "消した道標は戻せません。今日作った道標は、1 日に作れる数を数えるため、作った日時だけを翌日の 0 時まで残します。";

export const LEAVE_LABEL = "退会してデータを全て消す";

export const CONFIRM_LEAVE_LABEL = "本当に退会する";

export const LEAVE_KEEPS =
  "今日作った道標は、1 日に作れる数を数えるため、作った日時だけを誰のものか分からない形で翌日の 0 時まで残します。";

export function deletePlanLabel(occupation: string): string {
  return `${occupation}の道標を消す`;
}

export const LEFT_NOTICE =
  "退会しました。ログアウトしてトップへ戻ります。戻らないときは、下のボタンでログアウトしてください。";

export function deletedPlanLabel(occupation: string): string {
  return `${occupation}の道標を消しました`;
}

export type TakenCount = { count: number } | { failure: string };

export function leaveSummary(
  plans: number,
  taken: TakenCount | undefined,
): string {
  const takenCount =
    taken && "count" in taken
      ? `もう取ったと答えた授業 ${taken.count} 科目`
      : "もう取ったと答えた授業";
  const failure =
    taken && "failure" in taken
      ? `もう取ったと答えた授業の数は確かめられませんでした(${taken.failure})。`
      : "";
  return `作った道標 ${plans} 件と、${takenCount}を全て消し、ログアウトします。${failure}`;
}
