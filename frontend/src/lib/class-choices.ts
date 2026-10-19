import type { ClassChoices } from "@/lib/api/client";

export function offeredClasses(
  choices: ClassChoices | undefined,
  chosen: Record<string, string>,
): Record<string, string> {
  const offered = new Map(
    (choices?.courses ?? []).map((course) => [course.name, course.class_codes]),
  );
  return Object.fromEntries(
    Object.entries(chosen).filter(([name, code]) =>
      offered.get(name)?.includes(code),
    ),
  );
}
