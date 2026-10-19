import type { PlanStatus } from "@/lib/api/client";

export const POLL_INTERVAL_MS = 2_000;
export const POLL_LIMIT_MS = 180_000;

export type Watch = "waiting" | "finished" | "gave-up";

export function watchState(status: PlanStatus, elapsedMs: number): Watch {
  if (status === "succeeded" || status === "failed") {
    return "finished";
  }
  return elapsedMs >= POLL_LIMIT_MS ? "gave-up" : "waiting";
}
