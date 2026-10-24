import AxeBuilder from "@axe-core/playwright";
import { type BrowserContext, type Page, expect, test } from "@playwright/test";

import {
  CLASS_CHOICES,
  DONE_PLAN,
  FAILED_PLAN,
  PLAN_LIST,
  RUNNING_PLAN,
  TAKEN_COURSES,
  answerApi,
  chooseDarkTheme,
  planApi,
  signIn,
} from "./fixtures";

const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
const WIDTHS = [375, 1280];
const NARROWEST = 320;

type Screen = {
  name: string;
  path: string;
  signedIn: boolean;
  answers: Record<string, unknown>;
  ready: (page: Page) => Promise<void>;
};

const SCREENS: Screen[] = [
  {
    name: "トップ(ログイン前)",
    path: "/",
    signedIn: false,
    answers: {},
    ready: (page) =>
      expect(page.getByRole("heading", { level: 1 })).toBeVisible(),
  },
  {
    name: "ログイン",
    path: "/login",
    signedIn: false,
    answers: {},
    ready: (page) =>
      expect(
        page.getByRole("button", { name: "Google でログイン" }),
      ).toBeVisible(),
  },
  {
    name: "利用規約",
    path: "/terms",
    signedIn: false,
    answers: {},
    ready: (page) =>
      expect(page.getByRole("heading", { level: 1 })).toBeVisible(),
  },
  {
    name: "プライバシーポリシー",
    path: "/privacy",
    signedIn: false,
    answers: {},
    ready: (page) =>
      expect(page.getByRole("heading", { level: 1 })).toBeVisible(),
  },
  {
    name: "無いページ",
    path: "/no-such-page",
    signedIn: false,
    answers: {},
    ready: (page) =>
      expect(
        page.getByRole("heading", { name: "ページが見つかりません" }),
      ).toBeVisible(),
  },
  {
    name: "入力",
    path: "/",
    signedIn: true,
    answers: {
      "/api/class-choices": CLASS_CHOICES,
      "/api/taken-courses": TAKEN_COURSES,
    },
    ready: (page) =>
      expect(page.getByRole("button", { name: "道標を作る" })).toBeEnabled(),
  },
  {
    name: "自分の道標",
    path: "/plans",
    signedIn: true,
    answers: { "/api/plans": PLAN_LIST, "/api/taken-courses": TAKEN_COURSES },
    ready: (page) =>
      expect(
        page.getByRole("link", { name: /データサイエンティスト/ }),
      ).toBeVisible(),
  },
  {
    name: "結果の道のり",
    path: `/plans/${DONE_PLAN.id}`,
    signedIn: true,
    answers: { [planApi(DONE_PLAN)]: DONE_PLAN },
    ready: (page) =>
      expect(page.getByRole("navigation", { name: "路線図" })).toBeVisible(),
  },
  {
    name: "結果の時間割帳",
    path: `/plans/${DONE_PLAN.id}?view=timetable`,
    signedIn: true,
    answers: { [planApi(DONE_PLAN)]: DONE_PLAN },
    ready: (page) =>
      expect(page.getByRole("link", { name: "時間割帳" })).toHaveAttribute(
        "aria-current",
        "page",
      ),
  },
  {
    name: "作成中",
    path: `/plans/${RUNNING_PLAN.id}`,
    signedIn: true,
    answers: { [planApi(RUNNING_PLAN)]: RUNNING_PLAN },
    ready: (page) =>
      expect(
        page.getByRole("heading", { name: /道標を作っています/ }),
      ).toBeVisible(),
  },
  {
    name: "作れなかった道標",
    path: `/plans/${FAILED_PLAN.id}`,
    signedIn: true,
    answers: { [planApi(FAILED_PLAN)]: FAILED_PLAN },
    ready: (page) =>
      expect(
        page.getByRole("heading", { name: "道標を作れませんでした" }),
      ).toBeVisible(),
  },
];

async function open(
  page: Page,
  context: BrowserContext,
  screen: Screen,
  width: number,
  dark: boolean,
) {
  await page.setViewportSize({ width, height: 900 });
  if (screen.signedIn) {
    await signIn(context);
  }
  if (dark) {
    await chooseDarkTheme(page);
  }
  await answerApi(page, screen.answers);
  await page.goto(screen.path);
  await screen.ready(page);
}

for (const screen of SCREENS) {
  test.describe(screen.name, () => {
    for (const width of WIDTHS) {
      for (const dark of [false, true]) {
        test(`幅 ${width}px の${dark ? "暗い" : "明るい"}見た目で WCAG 2.2 の A と AA の違反が無い`, async ({
          page,
          context,
        }) => {
          await open(page, context, screen, width, dark);
          const results = await new AxeBuilder({ page })
            .withTags(WCAG_TAGS)
            .analyze();
          expect(
            results.violations.map((violation) => ({
              rule: violation.id,
              targets: violation.nodes.map((node) => node.target.join(" ")),
            })),
          ).toEqual([]);
        });
      }
    }

    test(`幅 ${NARROWEST}px で横にはみ出さない`, async ({ page, context }) => {
      await open(page, context, screen, NARROWEST, false);
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - window.innerWidth,
      );
      expect(overflow).toBeLessThanOrEqual(0);
    });
  });
}
