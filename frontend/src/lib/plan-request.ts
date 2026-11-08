import type { Plan, PlanRequest } from "@/lib/api/client";
import { OCCUPATION_REQUIRED, SAME_OCCUPATION_NOTE } from "@/lib/labels";

type Conditions = Plan["conditions"];

export const MAX_OCCUPATION_LENGTH = 100;

export function occupationProblem(occupation: string): string | null {
  return occupation.trim() ? null : OCCUPATION_REQUIRED;
}

export function rebuildProblem(
  occupation: string,
  conditions: Conditions,
): string | null {
  return (
    occupationProblem(occupation) ??
    (occupation.trim() === conditions.occupation ? SAME_OCCUPATION_NOTE : null)
  );
}

export function rebuildRequest(
  occupation: string,
  conditions: Conditions,
): PlanRequest {
  return {
    occupation: occupation.trim(),
    grade: conditions.grade,
    term: conditions.term,
    department: conditions.department,
    chosen_classes: conditions.chosen_classes,
    fixed_courses: conditions.fixed_courses,
  };
}
