import type {
  PlacedCourse,
  PlanResult,
  Relevance,
  SemesterPlan,
  Term,
} from "@/lib/api/client";

export type Hop = {
  name: string;
  section: string;
  station: number;
  semester: SemesterPlan;
};

export type Transfer = { mark: string; from: Hop; to: Hop };

export type TransferRoutes = {
  departures: Map<string, Transfer>;
  arrivals: Map<string, Transfer[]>;
};

type Stop = { course: PlacedCourse; station: number };

const MARKS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

function courseStops(semesters: SemesterPlan[]): Map<string, Stop> {
  const first = new Map<string, Stop>();
  semesters.forEach((semester, station) => {
    for (const course of semester.courses) {
      if (!first.has(course.name)) {
        first.set(course.name, { course, station });
      }
    }
  });
  return first;
}

function markOf(index: number): string {
  const letter = MARKS[index % MARKS.length];
  return index < MARKS.length
    ? letter
    : markOf(Math.floor(index / MARKS.length) - 1) + letter;
}

export function transferRoutes(semesters: SemesterPlan[]): TransferRoutes {
  const stops = courseStops(semesters);
  const hopOf = ({ course, station }: Stop): Hop => ({
    name: course.name,
    section: course.section_code,
    station,
    semester: semesters[station],
  });
  const legs = [...stops.values()].flatMap((stop) => {
    const pillar =
      stop.course.relevance === "foundation" &&
      stop.course.prerequisite_for !== null
        ? stops.get(stop.course.prerequisite_for)
        : undefined;
    return pillar?.course.relevance === "core"
      ? [{ from: hopOf(stop), to: hopOf(pillar) }]
      : [];
  });
  const targets = new Set(legs.map((leg) => leg.to.name));
  const arrivals = new Map(
    [...stops.keys()]
      .filter((name) => targets.has(name))
      .map((name, index): [string, Transfer[]] => [
        name,
        legs
          .filter((leg) => leg.to.name === name)
          .map((leg) => ({ mark: markOf(index), ...leg })),
      ]),
  );
  const departures = new Map(
    [...arrivals.values()]
      .flat()
      .map((transfer) => [transfer.from.name, transfer]),
  );
  return { departures, arrivals };
}

export function linkedNames(
  routes: TransferRoutes,
  focus: string | null,
): Set<string> {
  if (focus === null) {
    return new Set();
  }
  const own = routes.departures.get(focus);
  return new Set([
    ...(own ? [own.to.name] : []),
    ...(routes.arrivals.get(focus) ?? []).map((transfer) => transfer.from.name),
  ]);
}

export function semesterKey(semester: { grade: number; term: Term }): string {
  return `${semester.grade}-${semester.term}`;
}

export function semesterCourses(semester: SemesterPlan): PlacedCourse[] {
  return [...semester.courses, ...semester.continuing];
}

export function courseNames(
  result: Pick<PlanResult, "semesters" | "unplaced">,
): string[] {
  return [
    ...new Set(
      [...result.semesters.flatMap(semesterCourses), ...result.unplaced].map(
        (course) => course.name,
      ),
    ),
  ];
}

export function pickSemester(
  semesters: SemesterPlan[],
  key: string | null,
): SemesterPlan | undefined {
  return (
    semesters.find((semester) => semesterKey(semester) === key) ?? semesters[0]
  );
}

export function ticketSerials(semesters: SemesterPlan[]): Map<string, string> {
  const codes = semesters.flatMap((semester) =>
    semester.courses.map((course) => course.section_code),
  );
  return new Map(
    codes.map((code, index) => [code, String(index + 1).padStart(4, "0")]),
  );
}

export function routeTotals(
  semesters: SemesterPlan[],
): { credits: number } & Record<Relevance, number> {
  const courses = semesters.flatMap((semester) => semester.courses);
  return {
    credits: semesters.reduce((sum, semester) => sum + semester.credits, 0),
    core: courses.filter((course) => course.relevance === "core").length,
    foundation: courses.filter((course) => course.relevance === "foundation")
      .length,
  };
}
