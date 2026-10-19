import type {
  PlacedCourse,
  Relevance,
  SemesterPlan,
  Term,
} from "@/lib/api/client";

export type TransferOrder = "before" | "same" | "after";

export type Transfer = {
  pillar: string;
  station: number;
  semester: SemesterPlan;
  order: TransferOrder;
};

export function transfers(semesters: SemesterPlan[]): Map<string, Transfer> {
  const pillars = new Map<string, number>();
  semesters.forEach((semester, station) => {
    for (const course of semester.courses) {
      if (course.relevance === "core" && !pillars.has(course.name)) {
        pillars.set(course.name, station);
      }
    }
  });
  const found = new Map<string, Transfer>();
  semesters.forEach((semester, station) => {
    for (const course of semester.courses) {
      const pillar =
        course.relevance === "foundation" ? course.prerequisite_for : null;
      const pillarStation = pillar === null ? undefined : pillars.get(pillar);
      if (pillar !== null && pillarStation !== undefined) {
        found.set(course.name, {
          pillar,
          station: pillarStation,
          semester: semesters[pillarStation],
          order:
            station < pillarStation
              ? "before"
              : station === pillarStation
                ? "same"
                : "after",
        });
      }
    }
  });
  return found;
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
