import type { Locator, Page } from "@playwright/test";

import type { Plan } from "@/lib/api/client";
import { PRIVACY_TITLE, PROGRESS_HEADING } from "@/lib/labels";
import { SAMPLE_PLAN } from "@/lib/sample-plan";

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

function plateText(page: Page, destination: string): Locator {
  return page.getByText(`${destination}行`, { exact: true });
}

async function renderedLines(text: Locator): Promise<string[]> {
  await fontsReady(text.page());
  return text.evaluate((element) => {
    const characters = new Intl.Segmenter("ja", { granularity: "grapheme" });
    const lines: { top: number; text: string }[] = [];
    const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT, {
      acceptNode: (node) =>
        node.parentElement?.closest(".sr-only")
          ? NodeFilter.FILTER_REJECT
          : NodeFilter.FILTER_ACCEPT,
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

async function openPlan(page: Page, api: Api, plan: Plan, width: number) {
  await signIn(page);
  api.answer({ [planApi(plan)]: plan });
  await page.setViewportSize({ width, height: 900 });
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
        await openPlan(page, api, screen.plan(destination), width);
        const text = plateText(page, destination);
        await expect(text).toBeVisible();
        expect(await renderedLines(text)).toEqual(expected[screen.name]);
      });
    }
  }

  test(`幅 ${width}px の作成中の画面で、見出しを句の途中で折らない`, async ({
    page,
    api,
  }) => {
    await openPlan(page, api, asRunning(SAMPLE_PLAN), width);
    const heading = page.getByRole("heading", { level: 1 });
    await expect(heading).toBeVisible();
    const lines = await renderedLines(heading);
    expect(isPhraseGrouping(lines, PROGRESS_HEADING), lines.join(" / ")).toBe(
      true,
    );
  });

  test(`幅 ${width}px のプライバシーポリシーで、見出しを句の途中で折らない`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/privacy");
    const heading = page.getByRole("heading", { level: 1 });
    await expect(heading).toBeVisible();
    const lines = await renderedLines(heading);
    expect(isPhraseGrouping(lines, PRIVACY_TITLE), lines.join(" / ")).toBe(
      true,
    );
  });
}
