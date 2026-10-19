import type {
  PlacedCourse,
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

export function transfers(semesters: SemesterPlan[]): Map<string, Transfer> {
  const pillars = new Map<string, { station: number; section: string }>();
  semesters.forEach((semester, station) => {
    for (const course of semester.courses) {
      if (course.relevance === "core" && !pillars.has(course.name)) {
        pillars.set(course.name, { station, section: course.section_code });
      }
    }
  });
  const found = new Map<string, Transfer>();
  for (const semester of semesters) {
    for (const course of semester.courses) {
      const pillar =
        course.relevance === "foundation" ? course.prerequisite_for : null;
      const target = pillar === null ? undefined : pillars.get(pillar);
      if (pillar !== null && target !== undefined) {
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

export function pickSemester(
  semesters: SemesterPlan[],
  key: string | null,
): SemesterPlan | undefined {
  return (
    semesters.find((semester) => semesterKey(semester) === key) ?? semesters[0]
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
