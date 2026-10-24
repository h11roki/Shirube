import type { Locator, Page } from "@playwright/test";

import type { Plan } from "@/lib/api/client";
import { SAMPLE_PLAN } from "@/lib/sample-plan";

import { expect, planApi, signIn, test } from "./fixtures";

const NARROW_WIDTHS = [320, 375];
const LONG_PLATES = [
  {
    destination: "組込みソフトウェアエンジニア",
    lines: ["組込みソフトウェア", "エンジニア行"],
  },
  {
    destination: "半導体・LSI 設計エンジニア",
    lines: ["半導体・LSI", "設計エンジニア行"],
  },
  {
    destination: "電子情報システム保守技術者",
    lines: ["電子情報システム", "保守技術者行"],
  },
];

function plateText(page: Page, destination: string): Locator {
  return page.getByText(`${destination}行`, { exact: true });
}

async function renderedLines(text: Locator): Promise<string[]> {
  await text.page().evaluate(async () => {
    await document.fonts.ready;
  });
  return text.evaluate((element) => {
    const lines: { top: number; text: string }[] = [];
    const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      const content = node.textContent ?? "";
      for (let index = 0; index < content.length; index += 1) {
        const range = document.createRange();
        range.setStart(node, index);
        range.setEnd(node, index + 1);
        const top = range.getBoundingClientRect().top;
        const line = lines.find((each) => Math.abs(each.top - top) < 4);
        if (line) {
          line.text += content[index];
        } else {
          lines.push({ top, text: content[index] });
        }
      }
    }
    return lines.map((line) => line.text.trim());
  });
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

  for (const { destination, lines } of LONG_PLATES) {
    test(`幅 ${width}px で、${destination}の板を語の切れ目で折る`, async ({
      page,
      api,
    }) => {
      const plan: Plan = {
        ...SAMPLE_PLAN,
        result: {
          ...SAMPLE_PLAN.result,
          profile: {
            ...SAMPLE_PLAN.result.profile,
            interpretation: destination,
          },
        },
      };
      await signIn(page);
      api.answer({ [planApi(plan)]: plan });
      await page.setViewportSize({ width, height: 900 });
      await page.goto(`/plans/${plan.id}`);
      const text = plateText(page, destination);
      await expect(text).toBeVisible();
      expect(await renderedLines(text)).toEqual(lines);
    });
  }
}
