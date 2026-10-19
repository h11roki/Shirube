export type ResultView = "route" | "timetable";

export const VIEWS_ANCHOR = "views";

const VIEW_PARAM = "view";
const SEMESTER_PARAM = "semester";
const TIMETABLE: ResultView = "timetable";

export function readResultView(params: Pick<URLSearchParams, "get">): {
  view: ResultView;
  semester: string | null;
} {
  return {
    view: params.get(VIEW_PARAM) === TIMETABLE ? TIMETABLE : "route",
    semester: params.get(SEMESTER_PARAM),
  };
}

export function resultViewHref(
  pathname: string,
  view: ResultView,
  semester?: string | null,
): string {
  if (view !== TIMETABLE) {
    return pathname;
  }
  const params = new URLSearchParams({ [VIEW_PARAM]: TIMETABLE });
  if (semester) {
    params.set(SEMESTER_PARAM, semester);
  }
  return `${pathname}?${params}`;
}
