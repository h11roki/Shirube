import { type Page, test as base, expect } from "@playwright/test";
import { encode } from "next-auth/jwt";

import type {
  ClassChoices,
  Plan,
  PlanList,
  TakenCourses,
} from "@/lib/api/client";
import { SAMPLE_PLAN } from "@/lib/sample-plan";

import { E2E_AUTH_SECRET, E2E_ORIGIN } from "./env";

const SESSION_COOKIE = "authjs.session-token";

export function asRunning(plan: Plan): Plan {
  return { ...plan, status: "running", stage: "selecting", result: null };
}

export function asFailed(plan: Plan): Plan {
  return {
    ...plan,
    status: "failed",
    stage: null,
    result: null,
    failure: "授業の候補が見つかりませんでした。",
  };
}

export const RUNNING_PLAN = asRunning({
  ...SAMPLE_PLAN,
  id: "7f1c2a10-0000-4000-8000-000000000002",
  conditions: {
    ...SAMPLE_PLAN.conditions,
    occupation: "組込みエンジニア",
    grade: 2,
    term: "autumn",
  },
});

export const FAILED_PLAN = asFailed({
  ...SAMPLE_PLAN,
  id: "7f1c2a10-0000-4000-8000-000000000003",
  conditions: {
    ...SAMPLE_PLAN.conditions,
    occupation: "音響エンジニア",
    grade: 1,
    term: "spring",
  },
});

export const PLAN_LIST: PlanList = {
  plans: [
    { plan: RUNNING_PLAN, created_at: "2026-10-24T10:00:00+09:00" },
    { plan: SAMPLE_PLAN, created_at: "2026-10-23T09:00:00+09:00" },
    { plan: FAILED_PLAN, created_at: "2026-10-22T18:30:00+09:00" },
  ].map(({ plan, created_at }) => ({
    id: plan.id,
    status: plan.status,
    occupation: plan.conditions.occupation,
    grade: plan.conditions.grade,
    term: plan.conditions.term,
    created_at,
  })),
  total: 3,
};

export const CLASS_CHOICES: ClassChoices = {
  term: "spring",
  courses: [
    { name: "電子回路Ⅰ", class_codes: ["A", "B"] },
    { name: "英語 S1", class_codes: ["1", "2", "3"] },
  ],
};

export const TAKEN_COURSES: TakenCourses = { names: ["基礎製図"] };

type Method = "GET" | "POST" | "PUT" | "DELETE";

export type Reply = { status?: number; json?: unknown; delayMs?: number };

export type Api = {
  answer: (answers: Record<string, unknown>) => Promise<void>;
  respond: (
    method: Method,
    path: string,
    first: Reply,
    ...rest: Reply[]
  ) => Promise<void>;
};

export const test = base.extend<{ api: Api }>({
  api: [
    async ({ page }, use) => {
      const blocked: string[] = [];
      const extra: string[] = [];
      const leftovers: (() => string | undefined)[] = [];
      await page.route(
        (url) =>
          url.pathname.startsWith("/api/") &&
          !url.pathname.startsWith("/api/auth/"),
        (route) => {
          blocked.push(
            `${route.request().method()} ${new URL(route.request().url()).pathname}`,
          );
          return route.abort();
        },
      );
      await use({
        answer: async (answers) => {
          for (const [path, json] of Object.entries(answers)) {
            let served = false;
            leftovers.push(() => (served ? undefined : `GET ${path}`));
            await page.route(
              (url) => url.pathname === path,
              (route) => {
                if (route.request().method() !== "GET") {
                  return route.fallback();
                }
                served = true;
                return route.fulfill({ json });
              },
            );
          }
        },
        respond: async (method, path, ...replies) => {
          leftovers.push(() =>
            replies.length > 0
              ? `${method} ${path}(残り ${replies.length} 個)`
              : undefined,
          );
          await page.route(
            (url) => url.pathname === path,
            async (route) => {
              if (route.request().method() !== method) {
                return route.fallback();
              }
              const reply = replies.shift();
              if (!reply) {
                extra.push(`${method} ${path}`);
                return route.abort();
              }
              const { delayMs = 0, ...response } = reply;
              await new Promise((resolve) => setTimeout(resolve, delayMs));
              return route.fulfill(response);
            },
          );
        },
      });
      expect(blocked, "差し替えていない /api/ が呼ばれた").toEqual([]);
      expect(extra, "差し替えた答えより多く呼ばれた /api/").toEqual([]);
      expect(
        leftovers.map((leftover) => leftover()).filter(Boolean),
        "差し替えた答えを使い切らなかった /api/",
      ).toEqual([]);
    },
    { auto: true },
  ],
});

export { expect };

export function planApi(plan: Plan): string {
  return `/api/plans/${plan.id}`;
}

export async function signIn(page: Page) {
  const value = await encode({
    token: { name: "試験の利用者", sub: "e2e", googleSubject: "e2e" },
    secret: E2E_AUTH_SECRET,
    salt: SESSION_COOKIE,
  });
  await page
    .context()
    .addCookies([{ name: SESSION_COOKIE, value, url: E2E_ORIGIN }]);
}
