import { type Page, test as base, expect } from "@playwright/test";
import { encode } from "next-auth/jwt";

import type {
  ClassChoices,
  Plan,
  PlanList,
  TakenCourses,
} from "@/lib/api/client";
import { SAMPLE_PLAN } from "@/lib/sample-plan";
import { DARK_THEME, THEME_STORAGE_KEY } from "@/lib/theme";

import { E2E_AUTH_SECRET, E2E_ORIGIN } from "./env";

const SESSION_COOKIE = "authjs.session-token";

export const DONE_PLAN: Plan = SAMPLE_PLAN;

export const RUNNING_PLAN: Plan = {
  ...SAMPLE_PLAN,
  status: "running",
  stage: "selecting",
  result: null,
};

export const FAILED_PLAN: Plan = {
  ...SAMPLE_PLAN,
  status: "failed",
  result: null,
  failure: "授業の候補が見つかりませんでした。",
};

export const PLAN_LIST: PlanList = {
  plans: [
    {
      id: SAMPLE_PLAN.id,
      status: "succeeded",
      occupation: SAMPLE_PLAN.conditions.occupation,
      grade: SAMPLE_PLAN.conditions.grade,
      term: SAMPLE_PLAN.conditions.term,
      created_at: "2026-10-23T09:00:00+09:00",
    },
    {
      id: "7f1c2a10-0000-4000-8000-000000000002",
      status: "running",
      occupation: "組込みエンジニア",
      grade: 2,
      term: "autumn",
      created_at: "2026-10-24T10:00:00+09:00",
    },
    {
      id: "7f1c2a10-0000-4000-8000-000000000003",
      status: "failed",
      occupation: "音響エンジニア",
      grade: 1,
      term: "spring",
      created_at: "2026-10-22T18:30:00+09:00",
    },
  ],
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

export type Api = {
  answer: (answers: Record<string, unknown>) => Promise<void>;
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
          blocked.push(new URL(route.request().url()).pathname);
          return route.abort();
        },
      );
      await use({
        answer: async (answers) => {
          for (const [path, body] of Object.entries(answers)) {
            unused.add(path);
            await page.route(
              (url) => url.pathname === path,
              (route) => {
                unused.delete(path);
                return route.fulfill({ json: body });
              },
            );
          }
        },
      });
      expect(blocked, "差し替えていない /api/ が呼ばれた").toEqual([]);
      expect([...unused], "差し替えたのに呼ばれなかった /api/").toEqual([]);
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

export async function chooseDarkTheme(page: Page) {
  await page.addInitScript(
    ([key, value]) => localStorage.setItem(key, value),
    [THEME_STORAGE_KEY, DARK_THEME],
  );
}
