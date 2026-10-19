import type { components } from "@/lib/api/schema";

type Schemas = components["schemas"];
export type Plan = Schemas["PlanOut"];
export type PlanRequest = Schemas["PlanIn"];
export type PlanList = Schemas["PlanListOut"];
export type PlanSummary = Schemas["PlanSummaryOut"];
export type PlanResult = Schemas["ResultOut"];
export type ClassChoices = Schemas["ClassChoicesOut"];
export type SemesterPlan = Schemas["SemesterPlanOut"];
export type PlacedCourse = Schemas["PlacedCourseOut"];
export type Course = Schemas["CourseOut"];
export type PlanStatus = Schemas["PlanStatus"];
export type Relevance = Schemas["Relevance"];
export type Term = Schemas["Term"];
export type Weekday = Schemas["Weekday"];

const UNREACHABLE = "道標のサーバーとやり取りできませんでした";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

export async function requestJson<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, { ...init, cache: "no-store" });
  } catch {
    throw new ApiError(0, UNREACHABLE);
  }
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new ApiError(response.status, UNREACHABLE);
  }
  if (!response.ok) {
    const detail =
      typeof body === "object" &&
      body !== null &&
      "detail" in body &&
      typeof body.detail === "string"
        ? body.detail
        : UNREACHABLE;
    throw new ApiError(response.status, detail);
  }
  return body as T;
}

export function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : UNREACHABLE;
}

export function isTemporary(error: unknown): boolean {
  return (
    error instanceof ApiError && (error.status === 0 || error.status >= 500)
  );
}
