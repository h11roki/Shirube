import { type Page, test as base, expect } from "@playwright/test";
import { encode } from "next-auth/jwt";

import type {
  ClassChoices,
  OfferedCourses,
  PlacedCourse,
  Plan,
  PlanList,
  PlanResult,
  TakenCourses,
} from "@/lib/api/client";
import { SAMPLE_PLAN } from "@/lib/sample-plan";

import { E2E_AUTH_SECRET, E2E_ORIGIN } from "./env";

const SESSION_COOKIE = "authjs.session-token";

export type FinishedPlan = Plan & { result: PlanResult };

export function withSemesterCourses(
  plan: FinishedPlan,
  index: number,
  change: (courses: PlacedCourse[]) => PlacedCourse[],
): FinishedPlan {
  const credits = (courses: PlacedCourse[]) =>
    courses.reduce((total, course) => total + course.credits, 0);
  return {
    ...plan,
    result: {
      ...plan.result,
      semesters: plan.result.semesters.map((semester, at) => {
        if (at !== index) {
          return semester;
        }
        const courses = change(semester.courses);
        return {
          ...semester,
          credits:
            semester.credits + credits(courses) - credits(semester.courses),
          courses,
        };
      }),
    },
  };
}

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

export const READING = {
  occupation: "Webエンジニア",
  interpretation: "ITエンジニア",
  assumption:
    "Webエンジニアを、Web を含むソフトウェア開発全般の IT エンジニアとして読んだ",
  skills: SAMPLE_PLAN.result.profile.skills,
};

export const READING_PLAN: Plan = {
  ...RUNNING_PLAN,
  id: "7f1c2a10-0000-4000-8000-000000000004",
  stage: "searching",
  conditions: { ...RUNNING_PLAN.conditions, occupation: READING.occupation },
  reading: READING,
};

export const REREAD_PLAN: Plan = {
  ...SAMPLE_PLAN,
  id: "7f1c2a10-0000-4000-8000-000000000005",
  conditions: { ...SAMPLE_PLAN.conditions, occupation: READING.occupation },
  result: { ...SAMPLE_PLAN.result, profile: READING },
};

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

export const OFFERED_COURSES: OfferedCourses = {
  term: "spring",
  courses: [
    {
      name: "英語 S1",
      credits: 1,
      semesters: [{ grade: 1, term: "spring" }],
    },
    {
      name: "情報理工学と社会のかかわりを考えるキャリア形成特論",
      credits: 2,
      semesters: [
        { grade: 2, term: "autumn" },
        { grade: 3, term: "autumn" },
      ],
    },
    {
      name: "電子回路Ⅰ",
      credits: 2,
      semesters: [{ grade: 2, term: "spring" }],
    },
    {
      name: "電子回路Ⅱ",
      credits: 2,
      semesters: [{ grade: 2, term: "autumn" }],
    },
  ],
};

type Method = "GET" | "POST" | "PUT" | "DELETE";

type Reply = { status?: number; json?: unknown; until?: Promise<unknown> };

type Stub = {
  next: () => Reply | undefined;
  leftover: () => string | undefined;
};

export type Api = {
  answer: (answers: Record<string, unknown>) => void;
  respond: (
    method: Method,
    path: string,
    first: Reply,
    ...rest: Reply[]
  ) => void;
};

export const test = base.extend<{ api: Api }>({
  api: [
    async ({ page }, use) => {
      const stubs = new Map<string, Stub>();
      const blocked = new Set<string>();
      const extra = new Set<string>();
      function stub(call: string, entry: Stub) {
        if (stubs.has(call)) {
          throw new Error(`同じ /api/ を 2 度差し替えた: ${call}`);
        }
        stubs.set(call, entry);
      }
      await page.route(
        (url) =>
          url.pathname.startsWith("/api/") &&
          !url.pathname.startsWith("/api/auth/"),
        async (route) => {
          const call = `${route.request().method()} ${new URL(route.request().url()).pathname}`;
          const entry = stubs.get(call);
          const reply = entry?.next();
          if (!reply) {
            (entry ? extra : blocked).add(call);
            return route.abort();
          }
          const { until, ...response } = reply;
          await until;
          return route.fulfill(response);
        },
      );
      await use({
        answer: (answers) => {
          for (const [path, json] of Object.entries(answers)) {
            let served = false;
            stub(`GET ${path}`, {
              next: () => {
                served = true;
                return { json };
              },
              leftover: () => (served ? undefined : "一度も呼ばれなかった"),
            });
          }
        },
        respond: (method, path, ...replies) => {
          stub(`${method} ${path}`, {
            next: () => replies.shift(),
            leftover: () =>
              replies.length > 0 ? `残り ${replies.length} 個` : undefined,
          });
        },
      });
      expect([...blocked], "差し替えていない /api/ が呼ばれた").toEqual([]);
      expect([...extra], "差し替えた答えより多く呼ばれた /api/").toEqual([]);
      expect(
        [...stubs].flatMap(([call, entry]) => {
          const leftover = entry.leftover();
          return leftover ? [`${call}(${leftover})`] : [];
        }),
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

export async function fontsReady(page: Page) {
  await page.evaluate(async () => {
    await document.fonts.ready;
  });
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
