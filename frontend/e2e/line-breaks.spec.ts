import type { Locator, Page } from "@playwright/test";

import type { Plan } from "@/lib/api/client";
import { PRIVACY_TITLE, PROGRESS_HEADING } from "@/lib/labels";
import { SAMPLE_PLAN } from "@/lib/sample-plan";
import { CATCHPHRASE } from "@/lib/site";

import {
  type Api,
  asRunning,
  expect,
  fontsReady,
  planApi,
  signIn,
  test,
} from "./fixtures";

const NARROW_WIDTHS = [320, 375];

const SCREENS: {
  name: string;
  plan: (destination: string) => Plan;
}[] = [
  {
    name: "結果の画面",
    plan: (destination) => ({
      ...SAMPLE_PLAN,
      result: {
        ...SAMPLE_PLAN.result,
        profile: { ...SAMPLE_PLAN.result.profile, interpretation: destination },
      },
    }),
  },
  {
    name: "作成中の画面",
    plan: (destination) =>
      asRunning({
        ...SAMPLE_PLAN,
        conditions: { ...SAMPLE_PLAN.conditions, occupation: destination },
      }),
  },
];

const LONG_PLATES: Record<string, Record<string, string[]>> = {
  組込みソフトウェアエンジニア: {
    結果の画面: ["組込みソフトウェア", "エンジニア行"],
    作成中の画面: ["組込み", "ソフトウェア", "エンジニア行"],
  },
  "半導体・LSI 設計エンジニア": {
    結果の画面: ["半導体・LSI", "設計エンジニア行"],
    作成中の画面: ["半導体・", "LSI 設計", "エンジニア行"],
  },
  電子情報システム保守技術者: {
    結果の画面: ["電子情報システム", "保守技術者行"],
    作成中の画面: ["電子情報", "システム", "保守技術者行"],
  },
};

const FIXED_HEADINGS: {
  screen: string;
  phrases: readonly string[];
  open: (page: Page, api: Api) => Promise<unknown>;
}[] = [
  {
    screen: "トップ",
    phrases: CATCHPHRASE,
    open: (page) => page.goto("/"),
  },
  {
    screen: "作成中の画面",
    phrases: PROGRESS_HEADING,
    open: (page, api) => openPlan(page, api, asRunning(SAMPLE_PLAN)),
  },
  {
    screen: "プライバシーポリシー",
    phrases: PRIVACY_TITLE,
    open: (page) => page.goto("/privacy"),
  },
];

function plateText(page: Page, destination: string): Locator {
  return page.getByText(`${destination}行`, { exact: true });
}

async function renderedLines(text: Locator): Promise<string[]> {
  await fontsReady(text.page());
  return text.evaluate((element) => {
    const characters = new Intl.Segmenter("ja", { granularity: "grapheme" });
    const lines: { top: number; text: string }[] = [];
    const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT, {
      acceptNode: (node) => {
        for (
          let parent = node.parentElement;
          parent && element.contains(parent);
          parent = parent.parentElement
        ) {
          const box = parent.getBoundingClientRect();
          if (box.width <= 1 && box.height <= 1) {
            return NodeFilter.FILTER_REJECT;
          }
        }
        return NodeFilter.FILTER_ACCEPT;
      },
    });
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      for (const { segment, index } of characters.segment(
        node.textContent ?? "",
      )) {
        const range = document.createRange();
        range.setStart(node, index);
        range.setEnd(node, index + segment.length);
        const top = range.getBoundingClientRect().top;
        const line = lines.find((each) => Math.abs(each.top - top) < 4);
        if (line) {
          line.text += segment;
        } else {
          lines.push({ top, text: segment });
        }
      }
    }
    return lines.map((line) => line.text.trim());
  });
}

function isPhraseGrouping(lines: string[], phrases: readonly string[]) {
  let next = 0;
  for (const line of lines) {
    let rest = line;
    while (rest.length > 0) {
      const phrase = phrases.at(next);
      if (phrase === undefined || !rest.startsWith(phrase)) {
        return false;
      }
      rest = rest.slice(phrase.length);
      next += 1;
    }
  }
  return next === phrases.length;
}

async function chromeLevelOneHeadingNames(page: Page) {
  const cdp = await page.context().newCDPSession(page);
  try {
    const { nodes } = await cdp.send("Accessibility.getFullAXTree");
    return nodes
      .filter(
        (node) =>
          !node.ignored &&
          node.role?.value === "heading" &&
          node.properties?.some(
            (property) =>
              property.name === "level" && property.value.value === 1,
          ),
      )
      .map((node) => node.name?.value);
  } finally {
    await cdp.detach();
  }
}

async function openPlan(page: Page, api: Api, plan: Plan) {
  await signIn(page);
  api.answer({ [planApi(plan)]: plan });
  await page.goto(`/plans/${plan.id}`);
}

for (const width of NARROW_WIDTHS) {
  test(`幅 ${width}px で、見本の行先表示の板を 1 行に収める`, async ({
    page,
  }) => {
    const destination = SAMPLE_PLAN.result.profile.interpretation;
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    const text = plateText(page, destination);
    await expect(text).toBeVisible();
    expect(await renderedLines(text)).toEqual([`${destination}行`]);
  });

  for (const screen of SCREENS) {
    for (const [destination, expected] of Object.entries(LONG_PLATES)) {
      test(`幅 ${width}px の${screen.name}で、${destination}の板を語の切れ目で折る`, async ({
        page,
        api,
      }) => {
        await page.setViewportSize({ width, height: 900 });
        await openPlan(page, api, screen.plan(destination));
        const text = plateText(page, destination);
        await expect(text).toBeVisible();
        expect(await renderedLines(text)).toEqual(expected[screen.name]);
      });
    }
  }

  for (const heading of FIXED_HEADINGS) {
    test(`幅 ${width}px の${heading.screen}で、見出しを句の途中で折らない`, async ({
      page,
      api,
    }) => {
      await page.setViewportSize({ width, height: 900 });
      await heading.open(page, api);
      const element = page.getByRole("heading", { level: 1 });
      await expect(element).toBeVisible();
      const lines = await renderedLines(element);
      expect(isPhraseGrouping(lines, heading.phrases), lines.join(" / ")).toBe(
        true,
      );
    });

    test(`幅 ${width}px で文字を 200% にしても、${heading.screen}の見出しが画面からはみ出さない`, async ({
      page,
      api,
    }) => {
      await page.setViewportSize({ width, height: 900 });
      await heading.open(page, api);
      const element = page.getByRole("heading", { level: 1 });
      await expect(element).toBeVisible();
      await page.addStyleTag({
        content: "html { font-size: 200% !important; }",
      });
      await fontsReady(page);
      expect(
        await element.evaluate((each) => each.getBoundingClientRect().right),
      ).toBeLessThanOrEqual(width);
    });
  }
}

for (const heading of FIXED_HEADINGS) {
  test(`${heading.screen}の見出しの読み上げの名前に、句のあいだの空白を入れない`, async ({
    page,
    api,
  }) => {
    await heading.open(page, api);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    const names = await chromeLevelOneHeadingNames(page);
    expect(names).toHaveLength(1);
    expect(names[0]).toContain(heading.phrases.join(""));
  });
}
