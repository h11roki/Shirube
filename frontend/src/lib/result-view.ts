export type ResultView = "route" | "timetable";

export const VIEWS_ANCHOR = "views";

const VIEW_PARAM = "view";
const SEMESTER_PARAM = "semester";

export function readResultView(params: Pick<URLSearchParams, "get">): {
  view: ResultView;
  semester: string | null;
} {
  return {
    view: params.get(VIEW_PARAM) === "timetable" ? "timetable" : "route",
    semester: params.get(SEMESTER_PARAM),
  };
}

export function resultViewHref(
  pathname: string,
  view: ResultView,
  semester?: string | null,
): string {
  if (view !== "timetable") {
    return pathname;
  }
  const params = new URLSearchParams({ [VIEW_PARAM]: "timetable" });
  if (semester) {
    params.set(SEMESTER_PARAM, semester);
  }
  return `${pathname}?${params}`;
}
