import type {
  PlacedCourse,
  PlanResult,
  Relevance,
  SemesterPlan,
  Term,
} from "@/lib/api/client";

export type Transfer = {
  pillar: string;
  pillarSection: string;
  station: number;
  semester: SemesterPlan;
};

export type Stop = { section: string; station: number; relevance: Relevance };

export function courseStops(semesters: SemesterPlan[]): Map<string, Stop> {
  const first = new Map<string, Stop>();
  semesters.forEach((semester, station) => {
    for (const course of semester.courses) {
      if (!first.has(course.name)) {
        first.set(course.name, {
          section: course.section_code,
          station,
          relevance: course.relevance,
        });
      }
    }
  });
  return first;
}

export function transfers(semesters: SemesterPlan[]): Map<string, Transfer> {
  const stops = courseStops(semesters);
  const found = new Map<string, Transfer>();
  for (const semester of semesters) {
    for (const course of semester.courses) {
      const pillar =
        course.relevance === "foundation" ? course.prerequisite_for : null;
      const target = pillar === null ? undefined : stops.get(pillar);
      if (pillar !== null && target?.relevance === "core") {
        found.set(course.name, {
          pillar,
          pillarSection: target.section,
          station: target.station,
          semester: semesters[target.station],
        });
      }
    }
  }
  return found;
}

export function linkedNames(
  found: Map<string, Transfer>,
  focus: string | null,
): Set<string> {
  const linked = new Set<string>();
  if (focus === null) {
    return linked;
  }
  const own = found.get(focus);
  if (own) {
    linked.add(own.pillar);
  }
  for (const [name, transfer] of found) {
    if (transfer.pillar === focus) {
      linked.add(name);
    }
  }
  return linked;
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
