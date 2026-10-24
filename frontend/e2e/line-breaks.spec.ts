import type { Locator, Page } from "@playwright/test";

import type { Plan } from "@/lib/api/client";
import { PRIVACY_TITLE, PROGRESS_HEADING } from "@/lib/labels";
import { resultViewHref } from "@/lib/result-view";
import { semesterCourses, semesterKey } from "@/lib/roadmap";
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

const SAMPLE_DESTINATION = SAMPLE_PLAN.result.profile.interpretation;

const SAMPLE_WORDS = ["データ", "サイエンティスト"];

function resultFor(destination: string): Plan {
  return {
    ...SAMPLE_PLAN,
    result: {
      ...SAMPLE_PLAN.result,
      profile: { ...SAMPLE_PLAN.result.profile, interpretation: destination },
    },
  };
}

const SCREENS: {
  name: string;
  plan: (destination: string) => Plan;
}[] = [
  { name: "結果の画面", plan: resultFor },
  {
    name: "作成中の画面",
    plan: (destination) =>
      asRunning({
        ...SAMPLE_PLAN,
        conditions: { ...SAMPLE_PLAN.conditions, occupation: destination },
      }),
  },
];

const LONG_DESTINATIONS = [
  ["組込み", "ソフトウェア", "エンジニア"],
  ["半導体・", "LSI ", "設計", "エンジニア"],
  ["電子", "情報", "システム", "保守", "技術者"],
];

const TICKET_NAMES = [
  ["データ", "エンジニアリング", "基礎"],
  ["データ", "サイエンス・", "AI", "基礎"],
  ["データ", "構造と", "アルゴリズム"],
  ["メディア", "情報", "処理"],
  ["ＡＩ・", "機械", "学習"],
  ["特殊", "講義", "（専門）Ⅲ", "（深層", "学習の", "応用）"],
];

const UNPLACED_PLAN: Plan = {
  ...SAMPLE_PLAN,
  result: {
    ...SAMPLE_PLAN.result,
    semesters: SAMPLE_PLAN.result.semesters.map((semester) => ({
      ...semester,
      courses: [],
      continuing: [],
    })),
    unplaced: SAMPLE_PLAN.result.semesters
      .flatMap(semesterCourses)
      .map(
        ({
          name,
          relevance,
          reason,
          prerequisite_for,
          syllabus_code,
          syllabus_url,
        }) => ({
          name,
          relevance,
          reason,
          prerequisite_for,
          syllabus_code,
          syllabus_url,
        }),
      ),
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

function endingWith(words: readonly string[], suffix: string): string[] {
  return words.map((word, index) =>
    index === words.length - 1 ? `${word}${suffix}` : word,
  );
}

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

function breaksOnlyBetween(lines: string[], parts: readonly string[]) {
  let next = 0;
  for (const line of lines) {
    let rest = line;
    while (rest.length > 0) {
      const part = parts.at(next);
      if (part === undefined) {
        return false;
      }
      if (rest.startsWith(part)) {
        rest = rest.slice(part.length);
      } else if (rest === part.trimEnd()) {
        rest = "";
      } else {
        return false;
      }
      next += 1;
    }
  }
  return next === parts.length;
}

async function escapedBox(text: Locator): Promise<string> {
  return text.evaluate((element) => {
    const range = document.createRange();
    range.selectNodeContents(element);
    const right = range.getBoundingClientRect().right;
    for (let box: Element | null = element; box; box = box.parentElement) {
      const style = getComputedStyle(box);
      const inner =
        box.getBoundingClientRect().right -
        parseFloat(style.paddingRight) -
        parseFloat(style.borderRightWidth);
      if (right > inner + 0.5) {
        return box.tagName;
      }
    }
    return "";
  });
}

async function hidesLastLine(text: Locator): Promise<boolean> {
  return text.evaluate((element) => {
    const range = document.createRange();
    range.selectNodeContents(element);
    const lines = range.getClientRects();
    const last = lines[lines.length - 1];
    return (
      !last ||
      (last.top + last.bottom) / 2 > element.getBoundingClientRect().bottom
    );
  });
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

async function expectBreaksBetweenWords(
  scope: Page | Locator,
  names: readonly (readonly string[])[],
) {
  for (const words of names) {
    const name = scope
      .getByRole("heading", { level: 3, name: words.join(""), exact: true })
      .first();
    await expect(name).toBeVisible();
    const lines = await renderedLines(name);
    expect(breaksOnlyBetween(lines, words), lines.join(" / ")).toBe(true);
    expect(await escapedBox(name), "字がはみ出した箱").toBe("");
  }
}

for (const width of NARROW_WIDTHS) {
  test(`幅 ${width}px で、見本の行先表示の板を 1 行に収める`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    const text = plateText(page, SAMPLE_DESTINATION);
    await expect(text).toBeVisible();
    expect(await renderedLines(text)).toEqual([`${SAMPLE_DESTINATION}行`]);
  });

  for (const screen of SCREENS) {
    for (const words of LONG_DESTINATIONS) {
      const destination = words.join("");
      test(`幅 ${width}px の${screen.name}で、${destination}の板を語の切れ目で折る`, async ({
        page,
        api,
      }) => {
        await page.setViewportSize({ width, height: 900 });
        await openPlan(page, api, screen.plan(destination));
        const text = plateText(page, destination);
        await expect(text).toBeVisible();
        const lines = await renderedLines(text);
        expect(
          breaksOnlyBetween(lines, endingWith(words, "行")),
          lines.join(" / "),
        ).toBe(true);
        expect(await escapedBox(text), "字がはみ出した箱").toBe("");
      });
    }
  }

  test(`幅 ${width}px の結果の画面で、見本の道のりの終わりを 1 行に収める`, async ({
    page,
    api,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    await openPlan(page, api, SAMPLE_PLAN);
    const end = page.getByRole("heading", {
      name: `${SAMPLE_DESTINATION}へ`,
      exact: true,
    });
    await expect(end).toBeVisible();
    expect(await renderedLines(end)).toEqual([`${SAMPLE_DESTINATION}へ`]);
  });

  for (const words of LONG_DESTINATIONS) {
    const destination = words.join("");
    test(`幅 ${width}px の結果の画面で、${destination}への道のりの終わりを語の切れ目で折る`, async ({
      page,
      api,
    }) => {
      await page.setViewportSize({ width, height: 900 });
      await openPlan(page, api, resultFor(destination));
      const end = page.getByRole("heading", {
        name: `${destination}へ`,
        exact: true,
      });
      await expect(end).toBeVisible();
      const lines = await renderedLines(end);
      expect(
        breaksOnlyBetween(lines, endingWith(words, "へ")),
        lines.join(" / "),
      ).toBe(true);
      expect(await escapedBox(end), "字がはみ出した箱").toBe("");
    });
  }

  test(`幅 ${width}px のトップで、見本の道のりの終わりを語の切れ目で折る`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    const end = page.getByRole("heading", {
      name: `${SAMPLE_DESTINATION}へ続きます`,
      exact: true,
    });
    await expect(end).toBeVisible();
    const lines = await renderedLines(end);
    expect(
      breaksOnlyBetween(lines, [...endingWith(SAMPLE_WORDS, "へ"), "続きます"]),
      lines.join(" / "),
    ).toBe(true);
    expect(await escapedBox(end), "字がはみ出した箱").toBe("");
  });

  for (const words of [SAMPLE_WORDS, ...LONG_DESTINATIONS]) {
    const destination = words.join("");
    test(`幅 ${width}px の結果の画面で、帯の終点の${destination}を語の切れ目で 2 行までに折る`, async ({
      page,
      api,
    }) => {
      await page.setViewportSize({ width, height: 900 });
      await openPlan(page, api, resultFor(destination));
      const goal = page
        .getByRole("navigation", { name: "路線図" })
        .getByRole("button", { name: destination, exact: true });
      await expect(goal).toBeVisible();
      const lines = await renderedLines(goal);
      expect(breaksOnlyBetween(lines, words), lines.join(" / ")).toBe(true);
      expect(lines.length).toBeLessThanOrEqual(2);
      expect(await hidesLastLine(goal), "帯の終点の最後の行が隠れる").toBe(
        false,
      );
    });
  }

  test(`幅 ${width}px の結果の画面で、帯の終点の行より長い語を 3 行までで切らずに出す`, async ({
    page,
    api,
  }) => {
    const destination = "データベースアドミニストレーター";
    await page.setViewportSize({ width, height: 900 });
    await openPlan(page, api, resultFor(destination));
    const goal = page
      .getByRole("navigation", { name: "路線図" })
      .getByRole("button", { name: destination, exact: true });
    await expect(goal).toBeVisible();
    const lines = await renderedLines(goal);
    expect(lines.join("")).toBe(destination);
    expect(await hidesLastLine(goal), "帯の終点の最後の行が隠れる").toBe(false);
  });

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
      expect(breaksOnlyBetween(lines, heading.phrases), lines.join(" / ")).toBe(
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

for (const width of [...NARROW_WIDTHS, 1280]) {
  test(`幅 ${width}px の結果の画面で、切符の授業名を語の切れ目でだけ折る`, async ({
    page,
    api,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    await openPlan(page, api, SAMPLE_PLAN);
    await expectBreaksBetweenWords(page, TICKET_NAMES);
  });

  test(`幅 ${width}px の結果の画面で、置けなかった授業の切符の授業名を語の切れ目でだけ折る`, async ({
    page,
    api,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    await openPlan(page, api, UNPLACED_PLAN);
    await expectBreaksBetweenWords(
      page
        .getByRole("heading", { level: 2, name: "置けなかった授業" })
        .locator(".."),
      TICKET_NAMES,
    );
  });

  test(`幅 ${width}px の時間割帳で、切符の授業名を語の切れ目でだけ折る`, async ({
    page,
    api,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    await signIn(page);
    api.answer({ [planApi(SAMPLE_PLAN)]: SAMPLE_PLAN });
    for (const words of TICKET_NAMES) {
      const semester = SAMPLE_PLAN.result.semesters.find((each) =>
        semesterCourses(each).some((course) => course.name === words.join("")),
      );
      await page.goto(
        resultViewHref(
          `/plans/${SAMPLE_PLAN.id}`,
          "timetable",
          semester && semesterKey(semester),
        ),
      );
      await expectBreaksBetweenWords(page, [words]);
    }
  });
}

for (const [width, place] of [
  [320, "下"],
  [375, "下"],
  [1280, "右"],
] as const) {
  test(`幅 ${width}px では、切符の半券を授業名の${place}に置く`, async ({
    page,
    api,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    await openPlan(page, api, SAMPLE_PLAN);
    const name = page
      .getByRole("heading", {
        level: 3,
        name: "データエンジニアリング基礎",
        exact: true,
      })
      .first();
    await expect(name).toBeVisible();
    const ticket = page.locator("article").filter({ has: name }).first();
    const nameBox = await name.boundingBox();
    const stubBox = await ticket.locator("dl").boundingBox();
    if (!nameBox || !stubBox) {
      throw new Error("切符の授業名か半券が描かれていない");
    }
    if (place === "下") {
      expect(stubBox.y).toBeGreaterThanOrEqual(nameBox.y + nameBox.height);
    } else {
      expect(stubBox.x).toBeGreaterThanOrEqual(nameBox.x + nameBox.width);
    }
  });
}

test("Intl.Segmenter の無いブラウザでも、トップの見本の道のりをサーバーで描いた形と食い違わせない", async ({
  page,
}) => {
  const reactErrors: string[] = [];
  page.on("pageerror", (error) => reactErrors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") {
      reactErrors.push(message.text());
    }
  });
  await page.addInitScript(() => {
    Reflect.deleteProperty(Intl, "Segmenter");
  });
  await page.goto("/");
  await expect(
    page.getByRole("heading", {
      name: `${SAMPLE_DESTINATION}へ続きます`,
      exact: true,
    }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "この学期の時間割を開く ▾" })
    .first()
    .click();
  await expect(
    page.getByRole("button", { name: "この学期の時間割を閉じる ▴" }),
  ).toBeVisible();
  expect(reactErrors.filter((error) => error.includes("React"))).toEqual([]);
});

for (const heading of FIXED_HEADINGS) {
  test(
    `${heading.screen}の見出しの読み上げの名前に、句のあいだの空白を入れない`,
    {
      tag: "@cdp",
    },
    async ({ page, api }) => {
      await heading.open(page, api);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      const names = await chromeLevelOneHeadingNames(page);
      expect(names).toHaveLength(1);
      expect(names[0]).toContain(heading.phrases.join(""));
    },
  );
}
