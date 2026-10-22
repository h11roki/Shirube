import type { components } from "@/lib/api/schema";

type Schemas = components["schemas"];
export type Plan = Schemas["PlanOut"];
export type PlanRequest = Schemas["PlanIn"];
export type PlanList = Schemas["PlanListOut"];
export type PlanSummary = Schemas["PlanSummaryOut"];
export type TakenCourses = Schemas["TakenCoursesOut"];
export type PlanResult = Schemas["ResultOut"];
export type ClassChoices = Schemas["ClassChoicesOut"];
export type SemesterPlan = Schemas["SemesterPlanOut"];
export type PlacedCourse = Schemas["PlacedCourseOut"];
export type Course = Schemas["CourseOut"];
export type PlanStatus = Schemas["PlanStatus"];
export type PlanStage = Schemas["PlanStage"];
export type Relevance = Schemas["Relevance"];
export type Term = Schemas["Term"];
export type Weekday = Schemas["Weekday"];

const UNREACHABLE = "道標のサーバーとやり取りできませんでした";
const UNAUTHORIZED = 401;
export const NOT_FOUND = 404;

const signedOutListeners = new Set<() => void>();
let signedOut = false;

function noteSignedOut() {
  if (signedOut) {
    return;
  }
  signedOut = true;
  for (const listener of signedOutListeners) {
    listener();
  }
}

export function subscribeSignedOut(listener: () => void): () => void {
  signedOutListeners.add(listener);
  return () => {
    signedOutListeners.delete(listener);
  };
}

export function hasSignedOut(): boolean {
  return signedOut;
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

async function send(path: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(path, { ...init, cache: "no-store" });
  } catch {
    throw new ApiError(0, UNREACHABLE);
  }
}

async function bodyOf(response: Response, init?: RequestInit) {
  try {
    return (await response.json()) as unknown;
  } catch {
    throw new ApiError(
      init?.signal?.aborted ? 0 : response.status,
      UNREACHABLE,
    );
  }
}

async function refusal(response: Response, init?: RequestInit) {
  if (response.status === UNAUTHORIZED) {
    noteSignedOut();
  }
  const body = await bodyOf(response, init);
  const detail =
    typeof body === "object" &&
    body !== null &&
    "detail" in body &&
    typeof body.detail === "string"
      ? body.detail
      : UNREACHABLE;
  return new ApiError(response.status, detail);
}

export async function requestJson<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await send(path, init);
  if (!response.ok) {
    throw await refusal(response, init);
  }
  return (await bodyOf(response, init)) as T;
}

export async function requestNothing(
  path: string,
  init?: RequestInit,
): Promise<void> {
  const response = await send(path, init);
  if (!response.ok) {
    throw await refusal(response, init);
  }
}

export function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : UNREACHABLE;
}

export function isTemporary(error: unknown): boolean {
  return (
    error instanceof ApiError && (error.status === 0 || error.status >= 500)
  );
}

export async function deletePlan(id: string): Promise<void> {
  try {
    await requestNothing(`/api/plans/${encodeURIComponent(id)}`, {
      method: "DELETE",
    });
  } catch (error) {
    if (!(error instanceof ApiError && error.status === NOT_FOUND)) {
      throw error;
    }
  }
}
