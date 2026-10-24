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

export const RUNNING_PLAN: Plan = {
  ...SAMPLE_PLAN,
  id: "7f1c2a10-0000-4000-8000-000000000002",
  status: "running",
  stage: "selecting",
  conditions: {
    ...SAMPLE_PLAN.conditions,
    occupation: "組込みエンジニア",
    grade: 2,
    term: "autumn",
  },
  result: null,
};

export const FAILED_PLAN: Plan = {
  ...SAMPLE_PLAN,
  id: "7f1c2a10-0000-4000-8000-000000000003",
  status: "failed",
  conditions: {
    ...SAMPLE_PLAN.conditions,
    occupation: "音響エンジニア",
    grade: 1,
    term: "spring",
  },
  result: null,
  failure: "授業の候補が見つかりませんでした。",
};

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

export type Reply = { status?: number; json?: unknown };

export type Api = {
  answer: (answers: Record<string, unknown>) => Promise<void>;
  respond: (method: string, path: string, ...replies: Reply[]) => Promise<void>;
};

export const test = base.extend<{ api: Api }>({
  api: [
    async ({ page }, use) => {
      const blocked: string[] = [];
      const unused = new Set<string>();
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
      async function respond(
        method: string,
        path: string,
        ...replies: Reply[]
      ) {
        const call = `${method} ${path}`;
        unused.add(call);
        let turn = 0;
        await page.route(
          (url) => url.pathname === path,
          (route) => {
            if (route.request().method() !== method) {
              return route.fallback();
            }
            const reply = replies[Math.min(turn, replies.length - 1)];
            turn += 1;
            if (turn >= replies.length) {
              unused.delete(call);
            }
            return route.fulfill(reply);
          },
        );
      }
      await use({
        answer: async (answers) => {
          for (const [path, json] of Object.entries(answers)) {
            await respond("GET", path, { json });
          }
        },
        respond,
      });
      expect(blocked, "差し替えていない /api/ が呼ばれた").toEqual([]);
      expect([...unused], "差し替えた答えを使い切らなかった /api/").toEqual([]);
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
