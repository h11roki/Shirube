import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";

import { TICKET_NOTCH_SHAPE } from "@/components/styles";
import { forgetTakenLabel } from "@/lib/labels";
import { SAMPLE_PLAN } from "@/lib/sample-plan";
import { DARK_THEME, THEME_STORAGE_KEY } from "@/lib/theme";

import {
  type Api,
  CLASS_CHOICES,
  FAILED_PLAN,
  PLAN_LIST,
  RUNNING_PLAN,
  TAKEN_COURSES,
  expect,
  fontsReady,
  planApi,
  signIn,
  test,
} from "./fixtures";

const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
const WIDTHS = [375, 1280];
const NARROWEST = 320;
const UNDECORATED_CSS = `
  body { background-image: none !important; }
  [data-station]::before, [data-station]::after,
  [class*="${TICKET_NOTCH_SHAPE}"]::before, [class*="${TICKET_NOTCH_SHAPE}"]::after { content: none !important; }
`;
const HAND_CHECKED_CONTRAST: Record<string, readonly string[] | undefined> = {
  nonBmp: ["→", "◇"],
  shortTextContent: ["柱"],
  bgOverlap: ["卒業", `${RUNNING_PLAN.conditions.grade} 回生`],
  elmPartiallyObscured: [SAMPLE_PLAN.conditions.occupation, "ダークモード"],
};

type Screen = {
  name: string;
  path: string;
  signedIn?: boolean;
  answers?: Record<string, unknown>;
  ready: (page: Page) => Promise<void>;
};

const SCREENS: Screen[] = [
  {
    name: "トップ(ログイン前)",
    path: "/",
    ready: (page) =>
      expect(
        page.getByRole("heading", { name: "自分の道標を作ってみる" }),
      ).toBeVisible(),
  },
  {
    name: "ログイン",
    path: "/login",
    ready: (page) =>
      expect(
        page.getByRole("button", { name: "Google でログイン" }),
      ).toBeVisible(),
  },
  {
    name: "利用規約",
    path: "/terms",
    ready: (page) =>
      expect(page.getByRole("heading", { level: 1 })).toBeVisible(),
  },
  {
    name: "プライバシーポリシー",
    path: "/privacy",
    ready: (page) =>
      expect(page.getByRole("heading", { level: 1 })).toBeVisible(),
  },
  {
    name: "無いページ",
    path: "/no-such-page",
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
    ready: async (page) => {
      await expect(
        page.getByRole("button", { name: "道標を作る" }),
      ).toBeEnabled();
      await page
        .getByText(
          `学科でクラスが分かれている科目(${CLASS_CHOICES.courses.length}科目、任意)`,
        )
        .click();
      await page
        .getByText(`もう取ったと答えた授業(${TAKEN_COURSES.names.length} 科目)`)
        .click();
      await expect(
        page.getByLabel(CLASS_CHOICES.courses[0].name),
      ).toBeVisible();
      await expect(
        page.getByRole("button", {
          name: forgetTakenLabel(TAKEN_COURSES.names[0]),
        }),
      ).toBeVisible();
    },
  },
  {
    name: "自分の道標",
    path: "/plans",
    signedIn: true,
    answers: { "/api/plans": PLAN_LIST },
    ready: (page) =>
      expect(
        page.getByRole("link", { name: /データサイエンティスト/ }),
      ).toBeVisible(),
  },
  {
    name: "結果の道のり",
    path: `/plans/${SAMPLE_PLAN.id}`,
    signedIn: true,
    answers: { [planApi(SAMPLE_PLAN)]: SAMPLE_PLAN },
    ready: (page) =>
      expect(page.getByRole("navigation", { name: "路線図" })).toBeVisible(),
  },
  {
    name: "結果の時間割帳",
    path: `/plans/${SAMPLE_PLAN.id}?view=timetable`,
    signedIn: true,
    answers: { [planApi(SAMPLE_PLAN)]: SAMPLE_PLAN },
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
  api: Api,
  screen: Screen,
  width: number,
  dark: boolean,
) {
  await page.setViewportSize({ width, height: 900 });
  if (screen.signedIn) {
    await signIn(page);
  }
  if (dark) {
    await page.addInitScript(
      ([key, value]) => localStorage.setItem(key, value),
      [THEME_STORAGE_KEY, DARK_THEME],
    );
  }
  api.answer(screen.answers ?? {});
  await page.goto(screen.path);
  await screen.ready(page);
  if (dark) {
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  }
  await fontsReady(page);
}

for (const screen of SCREENS) {
  test.describe(screen.name, () => {
    for (const width of WIDTHS) {
      for (const dark of [false, true]) {
        test(`幅 ${width}px の${dark ? "暗い" : "明るい"}見た目で WCAG 2.2 の A と AA の違反が無い`, async ({
          page,
          api,
        }) => {
          await open(page, api, screen, width, dark);
          await page.addStyleTag({ content: UNDECORATED_CSS });
          const results = await new AxeBuilder({ page })
            .withTags(WCAG_TAGS)
            .analyze();
          expect(
            results.violations.map((violation) => ({
              rule: violation.id,
              targets: violation.nodes.map((node) => node.target.join(" ")),
            })),
          ).toEqual([]);
          const undecided = results.incomplete.flatMap((item) =>
            item.nodes.map((node) => {
              const data = node.any[0]?.data as {
                messageKey?: string;
                contrastRatio?: number;
              } | null;
              return {
                rule: item.id,
                reason: data?.messageKey ?? "",
                measured: data?.contrastRatio ?? 0,
                target: node.target.join(" "),
              };
            }),
          );
          const texts = await page.evaluate(
            (targets) =>
              targets.map(
                (target) =>
                  document.querySelector(target)?.textContent?.trim() ?? "",
              ),
            undecided.map(({ target }) => target),
          );
          expect(
            undecided
              .map((item, index) => ({ ...item, text: texts[index] }))
              .filter(
                ({ rule, reason, measured, text }) =>
                  rule !== "color-contrast" ||
                  measured > 0 ||
                  !HAND_CHECKED_CONTRAST[reason]?.includes(text),
              ),
          ).toEqual([]);
        });
      }
    }

    test(`幅 ${NARROWEST}px で横にはみ出さない`, async ({ page, api }) => {
      await open(page, api, screen, NARROWEST, false);
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - window.innerWidth,
      );
      expect(overflow).toBeLessThanOrEqual(0);
    });

    for (const width of [NARROWEST, ...WIDTHS]) {
      test(`幅 ${width}px で文字を 200% にしても横にはみ出さない`, async ({
        page,
        api,
      }) => {
        await open(page, api, screen, width, false);
        await page.addStyleTag({
          content: "html { font-size: 200% !important; }",
        });
        await fontsReady(page);
        const report = await page.evaluate(() => {
          const wide = [...document.querySelectorAll("body *")]
            .filter(
              (element) =>
                element.getBoundingClientRect().right > window.innerWidth + 0.5,
            )
            .slice(0, 8)
            .map(
              (element) =>
                `${element.tagName} ${String(element.className).slice(0, 80)} ${Math.round(element.getBoundingClientRect().right)}`,
            );
          return {
            overflow: document.documentElement.scrollWidth - window.innerWidth,
            wide,
          };
        });
        expect(report.overflow, report.wide.join("\n")).toBeLessThanOrEqual(0);
      });
    }
  });
}
