import type { Locator, Page } from "@playwright/test";

import type { PlacedCourse, Plan, Relevance, Weekday } from "@/lib/api/client";
import {
  CANCEL_LABEL,
  CONFIRM_DELETE_LABEL,
  DELETE_PLAN_LABEL,
  NO_LESSONS_LABEL,
  answeredLabel,
  deletePlanLabel,
  deletedPlanLabel,
  markTakenLabel,
  stationLabel,
  syllabusLinkLabel,
  unmarkTakenLabel,
} from "@/lib/labels";
import { POLL_INTERVAL_MS } from "@/lib/polling";
import { SAMPLE_PLAN } from "@/lib/sample-plan";

import {
  CLASS_CHOICES,
  FAILED_PLAN,
  PLAN_LIST,
  RUNNING_PLAN,
  TAKEN_COURSES,
  asFailed,
  asRunning,
  expect,
  planApi,
  signIn,
  test,
} from "./fixtures";

const LATER = "01:00";
const NARROW_WIDTH = 320;
const WIDE_WIDTH = 1280;
const PAUSE_AHEAD_MS = 60_000;
const TAKEN = SAMPLE_PLAN.result.semesters[0].courses[0];
const CONFLICT = "ほかの画面の答えで道標が変わりました。";
const RUNNING_REFUSAL = "作成中の道標は消せません。";

const ASKED_PLAN: Plan = {
  ...SAMPLE_PLAN,
  result: { ...SAMPLE_PLAN.result, offered_earlier: [TAKEN.name] },
};

const MARKED_PLAN: Plan = {
  ...SAMPLE_PLAN,
  result: {
    ...SAMPLE_PLAN.result,
    semesters: SAMPLE_PLAN.result.semesters.map((semester, index) =>
      index === 0
        ? {
            ...semester,
            credits: semester.credits - TAKEN.credits,
            courses: semester.courses.filter(
              (course) => course.name !== TAKEN.name,
            ),
          }
        : semester,
    ),
    taken: [TAKEN],
    offered_earlier: [TAKEN.name],
  },
};

function lesson(
  name: string,
  relevance: Relevance,
  classCode: string,
  weekday: Weekday,
  period: number,
): PlacedCourse {
  return {
    ...SAMPLE_PLAN.result.semesters[0].courses[0],
    name,
    relevance,
    class_code: classCode,
    section_code: name,
    slots: [{ weekday, period }],
  };
}

const WEEK_PLAN: Plan = {
  ...SAMPLE_PLAN,
  result: {
    ...SAMPLE_PLAN.result,
    semesters: SAMPLE_PLAN.result.semesters.map((semester, index) =>
      index === 0
        ? {
            ...semester,
            courses: [
              lesson("信号処理", "core", "A", "mon", 2),
              lesson("電磁気学", "foundation", "B", "tue", 1),
              lesson("回路理論", "core", "A", "tue", 3),
            ],
            continuing: [],
          }
        : semester,
    ),
  },
};

function takenApi(name: string): string {
  return `${planApi(ASKED_PLAN)}/taken-courses/${encodeURIComponent(name)}`;
}

async function settle(page: Page) {
  await page.evaluate(
    () =>
      new Promise((resolve) => {
        const channel = new MessageChannel();
        channel.port1.onmessage = () => resolve(null);
        channel.port2.postMessage(null);
      }),
  );
}

async function openAskedPlan(page: Page) {
  await page.goto(`/plans/${ASKED_PLAN.id}`);
  await expect(
    page.getByRole("button", { name: markTakenLabel(TAKEN.name) }),
  ).toBeVisible();
  await page.clock.pauseAt(Date.now() + PAUSE_AHEAD_MS);
}

test.beforeEach(async ({ page }) => {
  await signIn(page);
});

test.describe("完成の知らせとタブの題", () => {
  test.beforeEach(async ({ page }) => {
    await page.clock.install();
  });

  test("作成中を見ていた道標ができたら、タブの題に「できました」を付けて読み上げる", async ({
    page,
    api,
  }) => {
    const polled = Promise.withResolvers<void>();
    api.respond(
      "GET",
      planApi(SAMPLE_PLAN),
      { json: asRunning(SAMPLE_PLAN) },
      { json: SAMPLE_PLAN, until: polled.promise },
    );
    await page.goto(`/plans/${SAMPLE_PLAN.id}`);
    await expect(page).toHaveTitle(/^作成中: /);
    polled.resolve();
    await page.clock.fastForward(POLL_INTERVAL_MS);
    await expect(page).toHaveTitle(/^できました: /);
    await expect(
      page.getByRole("status").filter({ hasText: "道標ができました" }),
    ).toHaveCount(1);
  });

  test("作成中を見ていた道標が作れなかったら、タブの題に「作れませんでした」を付け、できたとは読み上げない", async ({
    page,
    api,
  }) => {
    const polled = Promise.withResolvers<void>();
    api.respond(
      "GET",
      planApi(SAMPLE_PLAN),
      { json: asRunning(SAMPLE_PLAN) },
      { json: asFailed(SAMPLE_PLAN), until: polled.promise },
    );
    await page.goto(`/plans/${SAMPLE_PLAN.id}`);
    await expect(page).toHaveTitle(/^作成中: /);
    polled.resolve();
    await page.clock.fastForward(POLL_INTERVAL_MS);
    await expect(
      page.getByRole("heading", { name: "道標を作れませんでした" }),
    ).toBeVisible();
    await expect(page).toHaveTitle(/^作れませんでした: /);
    await settle(page);
    await page.clock.fastForward(LATER);
    await settle(page);
    await expect(
      page.getByRole("status").filter({ hasText: "道標ができました" }),
    ).toHaveCount(0);
  });

  test("初めからできていた道標は、タブの題を変えず読み上げない", async ({
    page,
    api,
  }) => {
    api.answer({ [planApi(SAMPLE_PLAN)]: SAMPLE_PLAN });
    await page.goto(`/plans/${SAMPLE_PLAN.id}`);
    await expect(
      page.getByRole("navigation", { name: "路線図" }),
    ).toBeVisible();
    await settle(page);
    await page.clock.fastForward(LATER);
    await settle(page);
    await expect(page).not.toHaveTitle(
      /^(作成中|できました|作れませんでした): /,
    );
    await expect(
      page.getByRole("status").filter({ hasText: "道標ができました" }),
    ).toHaveCount(0);
  });
});

test.describe("もう取った", () => {
  test.beforeEach(async ({ page }) => {
    await page.clock.install();
  });

  test("答えると、外して置き直したことを知らせてフォーカスを移し、知らせの「戻す」で元に戻す", async ({
    page,
    api,
  }) => {
    api.answer({ [planApi(ASKED_PLAN)]: ASKED_PLAN });
    api.respond("PUT", takenApi(TAKEN.name), { json: MARKED_PLAN });
    api.respond("DELETE", takenApi(TAKEN.name), { json: ASKED_PLAN });
    await openAskedPlan(page);
    await page
      .getByRole("button", { name: markTakenLabel(TAKEN.name) })
      .click();
    const marked = page
      .getByRole("status")
      .filter({ hasText: answeredLabel(TAKEN.name, "mark") });
    await expect(marked).toBeFocused();
    await expect(
      page.getByRole("button", { name: unmarkTakenLabel(TAKEN.name) }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: markTakenLabel(TAKEN.name) }),
    ).toHaveCount(0);
    await marked.getByRole("button", { name: "戻す" }).click();
    await expect(
      page
        .getByRole("status")
        .filter({ hasText: answeredLabel(TAKEN.name, "unmark") }),
    ).toBeFocused();
    await expect(
      page.getByRole("button", { name: markTakenLabel(TAKEN.name) }),
    ).toBeVisible();
  });

  test("マウスで答えた知らせは、しばらくすると消える", async ({
    page,
    api,
  }) => {
    api.answer({ [planApi(ASKED_PLAN)]: ASKED_PLAN });
    api.respond("PUT", takenApi(TAKEN.name), { json: MARKED_PLAN });
    await openAskedPlan(page);
    await page
      .getByRole("button", { name: markTakenLabel(TAKEN.name) })
      .click();
    const marked = page.getByText(answeredLabel(TAKEN.name, "mark"));
    await expect(marked).toBeVisible();
    await settle(page);
    await page.clock.fastForward(LATER);
    await expect(marked).toBeHidden();
  });

  test("マウスで答えたあと Tab で知らせの中へ移ると、知らせは消えない", async ({
    page,
    api,
  }) => {
    api.answer({ [planApi(ASKED_PLAN)]: ASKED_PLAN });
    api.respond("PUT", takenApi(TAKEN.name), { json: MARKED_PLAN });
    await openAskedPlan(page);
    await page
      .getByRole("button", { name: markTakenLabel(TAKEN.name) })
      .click();
    const marked = page.getByText(answeredLabel(TAKEN.name, "mark"));
    await expect(marked).toBeVisible();
    await settle(page);
    await page.keyboard.press("Tab");
    await expect(
      page.getByRole("status").getByRole("button", { name: "戻す" }),
    ).toBeFocused();
    await page.clock.fastForward(LATER);
    await settle(page);
    await expect(marked).toBeVisible();
    await page.keyboard.press("Tab");
    await expect(marked).toBeHidden();
  });

  test("キーボードで答えた知らせは、フォーカスがあるあいだ消えない", async ({
    page,
    api,
  }) => {
    api.answer({ [planApi(ASKED_PLAN)]: ASKED_PLAN });
    api.respond("PUT", takenApi(TAKEN.name), { json: MARKED_PLAN });
    await openAskedPlan(page);
    await page
      .getByRole("button", { name: markTakenLabel(TAKEN.name) })
      .focus();
    await page.keyboard.press("Enter");
    const marked = page.getByText(answeredLabel(TAKEN.name, "mark"));
    await expect(marked).toBeVisible();
    await settle(page);
    await page.clock.fastForward(LATER);
    await settle(page);
    await expect(marked).toBeVisible();
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");
    await expect(marked).toBeHidden();
  });

  test("キーボードで答え、返る前にほかのボタンをマウスで押しても、知らせはフォーカスが外へ移るまで残る", async ({
    page,
    api,
  }) => {
    const replied = Promise.withResolvers<void>();
    api.answer({ [planApi(ASKED_PLAN)]: ASKED_PLAN });
    api.respond("PUT", takenApi(TAKEN.name), {
      json: MARKED_PLAN,
      until: replied.promise,
    });
    await openAskedPlan(page);
    const mark = page.getByRole("button", {
      name: markTakenLabel(TAKEN.name),
    });
    await mark.focus();
    await page.keyboard.press("Enter");
    await expect(mark).toBeDisabled();
    await page.getByRole("button", { name: "ダークモード" }).click();
    replied.resolve();
    const marked = page.getByText(answeredLabel(TAKEN.name, "mark"));
    await expect(marked).toBeVisible();
    await settle(page);
    await page.clock.fastForward(LATER);
    await settle(page);
    await expect(marked).toBeVisible();
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");
    await expect(marked).toBeHidden();
  });

  test("断られたら断りの文を知らせ、道標を読み直す", async ({ page, api }) => {
    api.respond(
      "GET",
      planApi(ASKED_PLAN),
      { json: ASKED_PLAN },
      { json: MARKED_PLAN },
    );
    api.respond("PUT", takenApi(TAKEN.name), {
      status: 409,
      json: { detail: CONFLICT },
    });
    await openAskedPlan(page);
    await page
      .getByRole("button", { name: markTakenLabel(TAKEN.name) })
      .click();
    await expect(
      page.getByRole("status").filter({ hasText: CONFLICT }),
    ).toBeFocused();
    await expect(
      page.getByRole("button", { name: unmarkTakenLabel(TAKEN.name) }),
    ).toBeVisible();
  });
});

test.describe("もう取ったの半券(動きを減らさない設定)", () => {
  test.use({ contextOptions: { reducedMotion: "no-preference" } });

  test("答えを待つあいだ半券が裂け、断られたら切符に戻る", async ({
    page,
    api,
  }) => {
    const replied = Promise.withResolvers<void>();
    api.answer({ [planApi(ASKED_PLAN)]: ASKED_PLAN });
    api.respond("PUT", takenApi(TAKEN.name), {
      status: 409,
      json: { detail: CONFLICT },
      until: replied.promise,
    });
    await page.goto(`/plans/${ASKED_PLAN.id}`);
    const mark = page.getByRole("button", {
      name: markTakenLabel(TAKEN.name),
    });
    const stub = page.locator("article").filter({ has: mark }).locator("dl");
    await expect(stub).toHaveCSS("animation-name", "none");
    await mark.click();
    await expect(stub).toHaveCSS("animation-name", "tear");
    replied.resolve();
    await expect(
      page.getByRole("status").filter({ hasText: CONFLICT }),
    ).toBeFocused();
    await expect(stub).toHaveCSS("animation-name", "none");
    await expect(mark).toBeEnabled();
  });
});

test.describe("乗り換えの線", () => {
  const foundation = SAMPLE_PLAN.result.semesters[0].courses.filter(
    (course) => course.relevance === "foundation",
  )[0];

  function ticketOf(page: Page, name: string): Locator {
    return page
      .locator("article")
      .filter({ has: page.getByRole("heading", { name, exact: true }) });
  }

  for (const width of [NARROW_WIDTH, WIDE_WIDTH]) {
    test(`幅 ${width}px で、乗り換えのある切符に触れると柱まで線を引き、横にはみ出さず、離れると消す`, async ({
      page,
      api,
    }) => {
      await page.setViewportSize({ width, height: 800 });
      api.answer({ [planApi(SAMPLE_PLAN)]: SAMPLE_PLAN });
      await page.goto(`/plans/${SAMPLE_PLAN.id}`);
      const lines = page.locator("svg[data-transfer-lines]");
      await expect(lines).toHaveCSS("opacity", "0");
      await ticketOf(page, foundation.name).hover();
      await expect(lines.locator("path")).toHaveCount(1);
      await expect(lines).toHaveCSS("opacity", "1");
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth - innerWidth,
        ),
      ).toBeLessThanOrEqual(0);
      await page.mouse.move(0, 0);
      await expect(lines).toHaveCSS("opacity", "0");
    });
  }

  test("切符の中にフォーカスがあるときも線を引く", async ({ page, api }) => {
    api.answer({ [planApi(SAMPLE_PLAN)]: SAMPLE_PLAN });
    await page.goto(`/plans/${SAMPLE_PLAN.id}`);
    await ticketOf(page, foundation.name)
      .getByRole("link", { name: syllabusLinkLabel(foundation.name) })
      .focus();
    const lines = page.locator("svg[data-transfer-lines]");
    await expect(lines.locator("path")).toHaveCount(1);
    await expect(lines).toHaveCSS("opacity", "1");
  });

  test.describe("動きを減らさない設定", () => {
    test.use({ contextOptions: { reducedMotion: "no-preference" } });

    test("触れると線を引く動きを付け、離れて薄れたら線を外す", async ({
      page,
      api,
    }) => {
      api.answer({ [planApi(SAMPLE_PLAN)]: SAMPLE_PLAN });
      await page.goto(`/plans/${SAMPLE_PLAN.id}`);
      await ticketOf(page, foundation.name).hover();
      const path = page.locator("svg[data-transfer-lines] path");
      await expect(path).toHaveCSS("animation-name", "trace");
      await page.mouse.move(0, 0);
      await expect(path).toHaveCount(0);
    });
  });

  test("つながる切符が画面の外なら、端に駅番号と授業名の札を出す", async ({
    page,
    api,
  }) => {
    const later = SAMPLE_PLAN.result.semesters[1].courses.filter(
      (course) =>
        course.relevance === "foundation" && course.prerequisite_for !== null,
    )[0];
    await page.setViewportSize({ width: 375, height: 800 });
    api.answer({ [planApi(SAMPLE_PLAN)]: SAMPLE_PLAN });
    await page.goto(`/plans/${SAMPLE_PLAN.id}`);
    const ticket = ticketOf(page, later.name);
    await ticket.evaluate((element) =>
      element.scrollIntoView({ block: "center" }),
    );
    await ticket.hover();
    await expect(
      page.getByText(`↑ ${stationLabel(0)} ${later.prerequisite_for}`),
    ).toBeVisible();
  });
});

test.describe("道標を作る", () => {
  test("作って結果の画面に移ったあと、入力の画面に戻ると、職業名が空でもう一度作れる", async ({
    page,
    api,
  }) => {
    api.answer({
      "/api/class-choices": CLASS_CHOICES,
      "/api/taken-courses": TAKEN_COURSES,
      [planApi(SAMPLE_PLAN)]: SAMPLE_PLAN,
    });
    api.respond("POST", "/api/plans", { status: 202, json: SAMPLE_PLAN });
    await page.goto("/");
    await page
      .getByLabel("なりたい職業")
      .fill(SAMPLE_PLAN.conditions.occupation);
    await page.getByRole("button", { name: "道標を作る" }).click();
    await expect(page).toHaveURL(`/plans/${SAMPLE_PLAN.id}`);
    await expect(
      page.getByRole("button", { name: DELETE_PLAN_LABEL }),
    ).toBeVisible();
    await page
      .getByRole("navigation")
      .getByRole("link", { name: "道標を作る" })
      .click();
    await expect(page).toHaveURL("/");
    await expect(page.getByLabel("なりたい職業")).toHaveValue("");
    await expect(
      page.getByRole("button", { name: "道標を作る" }),
    ).toBeEnabled();
  });
});

test.describe("道標を消す", () => {
  test("結果の画面では、確かめてから消して一覧へ移り、やめるとフォーカスを消すのボタンに戻す", async ({
    page,
    api,
  }) => {
    api.answer({
      [planApi(SAMPLE_PLAN)]: SAMPLE_PLAN,
      "/api/plans": {
        plans: PLAN_LIST.plans.filter((plan) => plan.id !== SAMPLE_PLAN.id),
        total: PLAN_LIST.total - 1,
      },
    });
    api.respond("DELETE", planApi(SAMPLE_PLAN), { status: 204 });
    await page.goto(`/plans/${SAMPLE_PLAN.id}`);
    const start = page.getByRole("button", { name: DELETE_PLAN_LABEL });
    await start.click();
    await expect(
      page.getByRole("button", { name: CANCEL_LABEL }),
    ).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(start).toBeFocused();
    await start.click();
    await page.getByRole("button", { name: CONFIRM_DELETE_LABEL }).click();
    await expect(page).toHaveURL(/\/plans$/);
    await expect(
      page.getByRole("link", { name: RUNNING_PLAN.conditions.occupation }),
    ).toBeVisible();
  });

  test("作成中で消せないと断られたら、その場に断りの文を出す", async ({
    page,
    api,
  }) => {
    api.answer({ [planApi(RUNNING_PLAN)]: RUNNING_PLAN });
    api.respond("DELETE", planApi(RUNNING_PLAN), {
      status: 409,
      json: { detail: RUNNING_REFUSAL },
    });
    await page.goto(`/plans/${RUNNING_PLAN.id}`);
    await page.getByRole("button", { name: DELETE_PLAN_LABEL }).click();
    await page.getByRole("button", { name: CONFIRM_DELETE_LABEL }).click();
    await expect(
      page.getByRole("group", { name: DELETE_PLAN_LABEL }),
    ).toContainText(RUNNING_REFUSAL);
  });

  test("一覧では、確かめてから消し、その行を除いて消したことを知らせる", async ({
    page,
    api,
  }) => {
    const occupation = FAILED_PLAN.conditions.occupation;
    api.answer({ "/api/plans": PLAN_LIST });
    api.respond("DELETE", planApi(FAILED_PLAN), { status: 204 });
    await page.goto("/plans");
    await page
      .getByRole("button", { name: deletePlanLabel(occupation) })
      .click();
    await page.getByRole("button", { name: CONFIRM_DELETE_LABEL }).click();
    await expect(page.getByText(deletedPlanLabel(occupation))).toBeFocused();
    await expect(page.getByRole("link", { name: occupation })).toHaveCount(0);
  });
});

test.describe("時間割帳の週", () => {
  test.beforeEach(({ api }) => {
    api.answer({ [planApi(WEEK_PLAN)]: WEEK_PLAN });
  });

  test("幅 640px 未満では曜日ごとの一覧にし、曜日を略さずに読ませる", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 375, height: 900 });
    await page.goto(`/plans/${WEEK_PLAN.id}?view=timetable`);
    await expect(page.locator("dl").filter({ hasText: NO_LESSONS_LABEL }))
      .toMatchAriaSnapshot(`
      - term: 月曜日
      - definition: 2 限 信号処理 柱 ・ A
      - term: 火曜日
      - definition: 1 限 電磁気学 礎 ・ B 3 限 回路理論 柱 ・ A
      - term: 水曜日
      - definition: 授業なし
      - term: 木曜日
      - definition: 授業なし
      - term: 金曜日
      - definition: 授業なし
    `);
    await expect(page.getByRole("table")).toBeHidden();
  });

  test("幅 640px 以上では表にし、列の見出しを曜日の名前で読ませる", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto(`/plans/${WEEK_PLAN.id}?view=timetable`);
    await expect(
      page.getByRole("columnheader", { name: "月曜日" }),
    ).toBeVisible();
    await expect(
      page.locator("dl").filter({ hasText: NO_LESSONS_LABEL }),
    ).toBeHidden();
  });
});

test.describe("見た目の切り替え", () => {
  for (const { width, gutter } of [
    { width: 375, gutter: 16 },
    { width: 680, gutter: 24 },
  ]) {
    test(`幅 ${width}px では、ロゴの行の右端に置き、ナビを次の行に回し、Tab もロゴ、切り替え、ナビの順に移る`, async ({
      page,
    }) => {
      await page.setViewportSize({ width, height: 800 });
      const { logo, toggle, nav } = await openHeader(page);
      const [logoBox, toggleBox, navBox] = await boxesOf(logo, toggle, nav);
      expect(toggleBox.y).toBeLessThan(logoBox.y + logoBox.height);
      expect(toggleBox.y + toggleBox.height).toBeLessThanOrEqual(navBox.y);
      expect(toggleBox.x + toggleBox.width).toBeCloseTo(width - gutter, 0);
    });
  }

  test("幅 1280px では、ロゴとナビのあいだに並べ、Tab もロゴ、切り替え、ナビの順に移る", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    const { logo, toggle, nav } = await openHeader(page);
    const [logoBox, toggleBox, navBox] = await boxesOf(logo, toggle, nav);
    expect(logoBox.x + logoBox.width).toBeLessThan(toggleBox.x);
    expect(toggleBox.x + toggleBox.width).toBeLessThan(navBox.x);
    expect(toggleBox.y).toBeLessThan(navBox.y + navBox.height);
    expect(navBox.y).toBeLessThan(toggleBox.y + toggleBox.height);
  });
});

async function openHeader(page: Page) {
  await page.goto("/terms");
  const banner = page.getByRole("banner");
  const logo = banner.getByRole("link", { name: "shirube" });
  const toggle = banner.getByRole("button", { name: "ダークモード" });
  const nav = banner.getByRole("link", { name: "道標を作る" });
  await logo.focus();
  await page.keyboard.press("Tab");
  await expect(toggle).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(nav).toBeFocused();
  return { logo, toggle, nav };
}

async function boxesOf(...locators: Locator[]) {
  return Promise.all(
    locators.map(async (locator) => {
      const box = await locator.boundingBox();
      expect(box).not.toBeNull();
      return box!;
    }),
  );
}
