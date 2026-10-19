import type {
  PlacedCourse,
  Relevance,
  SemesterPlan,
  Term,
} from "@/lib/api/client";

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
