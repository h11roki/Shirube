export type ResultView = "route" | "timetable";

export const VIEWS_ANCHOR = "views";

const VIEW_PARAM = "view";
const SEMESTER_PARAM = "semester";

const IN_VIEW = 0.4;

export function activeStation(
  tops: number[],
  viewportHeight: number,
  scrolledToEnd: boolean,
): number {
  if (scrolledToEnd) {
    return tops.length - 1;
  }
  let current = 0;
  tops.forEach((top, index) => {
    if (top < viewportHeight * IN_VIEW) {
      current = index;
    }
  });
  return Math.max(0, current);
}

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
