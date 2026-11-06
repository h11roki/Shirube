import type { OfferedCourse, OfferedCourses } from "@/lib/api/client";

export const MAX_FIXED_COURSES = 30;

export function chosenCourses(
  offered: OfferedCourses | undefined,
  chosen: readonly string[],
): OfferedCourse[] {
  const names = new Set(chosen);
  return (offered?.courses ?? []).filter((course) => names.has(course.name));
}

export function toggledCourses(
  chosen: readonly OfferedCourse[],
  name: string,
): string[] {
  const names = chosen.map((course) => course.name);
  return names.includes(name)
    ? names.filter((each) => each !== name)
    : [...names, name];
}

function searchable(text: string): string {
  return text.normalize("NFKC").toLowerCase();
}

export function matchingCourses(
  courses: readonly OfferedCourse[],
  filter: string,
): OfferedCourse[] {
  const words = searchable(filter).split(/\s+/).filter(Boolean);
  return courses.filter((course) => {
    const name = searchable(course.name);
    return words.every((word) => name.includes(word));
  });
}
