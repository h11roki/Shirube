import type { Locator, Page } from "@playwright/test";

import type { Plan } from "@/lib/api/client";
import { SAMPLE_PLAN } from "@/lib/sample-plan";

import { expect, planApi, signIn, test } from "./fixtures";

const LONG_DESTINATIONS = [
  "組込みソフトウェアエンジニア",
  "半導体・LSI 設計エンジニア",
];

function plateText(page: Page, destination: string): Locator {
  return page.getByText(`${destination}行`, { exact: true });
}

async function lineCount(text: Locator): Promise<number> {
  await text.page().evaluate(async () => {
    await document.fonts.ready;
  });
  return text.evaluate((element) =>
    Math.round(
      element.getBoundingClientRect().height /
        parseFloat(getComputedStyle(element).lineHeight),
    ),
  );
}

function wordsAcrossLines(text: Locator): Promise<string[]> {
  return text.evaluate((element) => {
    const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
    const across: string[] = [];
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      const range = document.createRange();
      range.selectNodeContents(node);
      if (range.getClientRects().length > 1) {
        across.push(node.textContent ?? "");
      }
    }
    return across;
  });
}

for (const width of [320, 375]) {
  test(`幅 ${width}px で、見本の行先表示の板を 1 行に収める`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    const text = plateText(page, SAMPLE_PLAN.result.profile.interpretation);
    await expect(text).toBeVisible();
    expect(await lineCount(text)).toBe(1);
  });
}

for (const destination of LONG_DESTINATIONS) {
  test(`幅 320px で、${destination}の板を語の途中で折らない`, async ({
    page,
    api,
  }) => {
    const plan: Plan = {
      ...SAMPLE_PLAN,
      result: {
        ...SAMPLE_PLAN.result,
        profile: { ...SAMPLE_PLAN.result.profile, interpretation: destination },
      },
    };
    await signIn(page);
    api.answer({ [planApi(plan)]: plan });
    await page.setViewportSize({ width: 320, height: 900 });
    await page.goto(`/plans/${plan.id}`);
    const text = plateText(page, destination);
    await expect(text).toBeVisible();
    expect(await lineCount(text)).toBeGreaterThan(1);
    expect(await wordsAcrossLines(text)).toEqual([]);
  });
}
