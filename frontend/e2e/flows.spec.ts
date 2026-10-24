import type { Plan } from "@/lib/api/client";
import {
  CANCEL_LABEL,
  CONFIRM_DELETE_LABEL,
  DELETE_PLAN_LABEL,
  NO_LESSONS_LABEL,
  answeredLabel,
  deletePlanLabel,
  deletedPlanLabel,
  markTakenLabel,
  unmarkTakenLabel,
} from "@/lib/labels";
import { POLL_INTERVAL_MS } from "@/lib/polling";
import { SAMPLE_PLAN } from "@/lib/sample-plan";

import {
  FAILED_PLAN,
  PLAN_LIST,
  RUNNING_PLAN,
  expect,
  planApi,
  signIn,
  test,
} from "./fixtures";

const LATER = "01:00";
const TAKEN = SAMPLE_PLAN.result.semesters[0].courses[0];
const CONFLICT = "ほかの画面の答えで道標が変わりました。";
const RUNNING_REFUSAL = "作成中の道標は消せません。";

const SAMPLE_RUNNING: Plan = {
  ...SAMPLE_PLAN,
  status: "running",
  stage: "selecting",
  result: null,
};

const SAMPLE_FAILED: Plan = {
  ...SAMPLE_PLAN,
  status: "failed",
  result: null,
  failure: FAILED_PLAN.failure,
};

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

function takenApi(name: string): string {
  return `${planApi(ASKED_PLAN)}/taken-courses/${encodeURIComponent(name)}`;
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
    await api.respond(
      "GET",
      planApi(SAMPLE_PLAN),
      { json: SAMPLE_RUNNING },
      { json: SAMPLE_PLAN },
    );
    await page.goto(`/plans/${SAMPLE_PLAN.id}`);
    await expect(page).toHaveTitle(/^作成中: /);
    await page.clock.fastForward(POLL_INTERVAL_MS);
    await expect(page).toHaveTitle(/^できました: /);
    await expect(
      page.getByRole("status").filter({ hasText: "道標ができました" }),
    ).toHaveCount(1);
  });

  test("作成中を見ていた道標が作れなかったら、タブの題に「作れませんでした」を付ける", async ({
    page,
    api,
  }) => {
    await api.respond(
      "GET",
      planApi(SAMPLE_PLAN),
      { json: SAMPLE_RUNNING },
      { json: SAMPLE_FAILED },
    );
    await page.goto(`/plans/${SAMPLE_PLAN.id}`);
    await expect(page).toHaveTitle(/^作成中: /);
    await page.clock.fastForward(POLL_INTERVAL_MS);
    await expect(
      page.getByRole("heading", { name: "道標を作れませんでした" }),
    ).toBeVisible();
    await expect(page).toHaveTitle(/^作れませんでした: /);
  });

  test("初めからできていた道標は、タブの題を変えず読み上げない", async ({
    page,
    api,
  }) => {
    await api.answer({ [planApi(SAMPLE_PLAN)]: SAMPLE_PLAN });
    await page.goto(`/plans/${SAMPLE_PLAN.id}`);
    await expect(
      page.getByRole("navigation", { name: "路線図" }),
    ).toBeVisible();
    await page.clock.fastForward(LATER);
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
    await api.answer({ [planApi(ASKED_PLAN)]: ASKED_PLAN });
    await api.respond("PUT", takenApi(TAKEN.name), { json: MARKED_PLAN });
    await api.respond("DELETE", takenApi(TAKEN.name), { json: ASKED_PLAN });
    await page.goto(`/plans/${ASKED_PLAN.id}`);
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
    await api.answer({ [planApi(ASKED_PLAN)]: ASKED_PLAN });
    await api.respond("PUT", takenApi(TAKEN.name), { json: MARKED_PLAN });
    await page.goto(`/plans/${ASKED_PLAN.id}`);
    await page
      .getByRole("button", { name: markTakenLabel(TAKEN.name) })
      .click();
    const marked = page.getByText(answeredLabel(TAKEN.name, "mark"));
    await expect(marked).toBeVisible();
    await page.clock.fastForward(LATER);
    await expect(marked).toBeHidden();
  });

  test("マウスで答えたあと Tab で知らせの中へ移ると、知らせは消えない", async ({
    page,
    api,
  }) => {
    await api.answer({ [planApi(ASKED_PLAN)]: ASKED_PLAN });
    await api.respond("PUT", takenApi(TAKEN.name), { json: MARKED_PLAN });
    await page.goto(`/plans/${ASKED_PLAN.id}`);
    await page
      .getByRole("button", { name: markTakenLabel(TAKEN.name) })
      .click();
    const marked = page.getByText(answeredLabel(TAKEN.name, "mark"));
    await expect(marked).toBeVisible();
    await page.keyboard.press("Tab");
    await expect(
      page.getByRole("status").getByRole("button", { name: "戻す" }),
    ).toBeFocused();
    await page.clock.fastForward(LATER);
    await expect(marked).toBeVisible();
    await page.keyboard.press("Tab");
    await expect(marked).toBeHidden();
  });

  test("キーボードで答えた知らせは、フォーカスがあるあいだ消えない", async ({
    page,
    api,
  }) => {
    await api.answer({ [planApi(ASKED_PLAN)]: ASKED_PLAN });
    await api.respond("PUT", takenApi(TAKEN.name), { json: MARKED_PLAN });
    await page.goto(`/plans/${ASKED_PLAN.id}`);
    await page
      .getByRole("button", { name: markTakenLabel(TAKEN.name) })
      .focus();
    await page.keyboard.press("Enter");
    const marked = page.getByText(answeredLabel(TAKEN.name, "mark"));
    await expect(marked).toBeVisible();
    await page.clock.fastForward(LATER);
    await expect(marked).toBeVisible();
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");
    await expect(marked).toBeHidden();
  });

  test("断られたら断りの文を知らせ、道標を読み直す", async ({ page, api }) => {
    await api.respond(
      "GET",
      planApi(ASKED_PLAN),
      { json: ASKED_PLAN },
      { json: MARKED_PLAN },
    );
    await api.respond("PUT", takenApi(TAKEN.name), {
      status: 409,
      json: { detail: CONFLICT },
    });
    await page.goto(`/plans/${ASKED_PLAN.id}`);
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

test.describe("道標を消す", () => {
  test("結果の画面では、確かめてから消して一覧へ移り、やめるとフォーカスを消すのボタンに戻す", async ({
    page,
    api,
  }) => {
    await api.answer({
      [planApi(SAMPLE_PLAN)]: SAMPLE_PLAN,
      "/api/plans": {
        plans: PLAN_LIST.plans.filter((plan) => plan.id !== SAMPLE_PLAN.id),
        total: PLAN_LIST.total - 1,
      },
    });
    await api.respond("DELETE", planApi(SAMPLE_PLAN), { status: 204 });
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
    await expect(
      page.getByRole("link", { name: SAMPLE_PLAN.conditions.occupation }),
    ).toHaveCount(0);
  });

  test("作成中で消せないと断られたら、その場に断りの文を出す", async ({
    page,
    api,
  }) => {
    await api.answer({ [planApi(RUNNING_PLAN)]: RUNNING_PLAN });
    await api.respond("DELETE", planApi(RUNNING_PLAN), {
      status: 409,
      json: { detail: RUNNING_REFUSAL },
    });
    await page.goto(`/plans/${RUNNING_PLAN.id}`);
    await page.getByRole("button", { name: DELETE_PLAN_LABEL }).click();
    await page.getByRole("button", { name: CONFIRM_DELETE_LABEL }).click();
    await expect(
      page.getByRole("group", { name: DELETE_PLAN_LABEL }),
    ).toContainText(RUNNING_REFUSAL);
    await expect(page).toHaveURL(new RegExp(`/plans/${RUNNING_PLAN.id}$`));
  });

  test("一覧では、確かめてから消し、その行を除いて消したことを知らせる", async ({
    page,
    api,
  }) => {
    const occupation = FAILED_PLAN.conditions.occupation;
    await api.answer({ "/api/plans": PLAN_LIST });
    await api.respond("DELETE", planApi(FAILED_PLAN), { status: 204 });
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
  test.beforeEach(async ({ api }) => {
    await api.answer({ [planApi(SAMPLE_PLAN)]: SAMPLE_PLAN });
  });

  test("幅 640px 未満では曜日ごとの一覧にし、曜日を略さずに読ませる", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 375, height: 900 });
    await page.goto(`/plans/${SAMPLE_PLAN.id}?view=timetable`);
    await expect(page.locator("dl").filter({ hasText: NO_LESSONS_LABEL }))
      .toMatchAriaSnapshot(`
      - term: 月曜日
      - definition: 4 限 確率統計 柱 ・ 6B
      - term: 火曜日
      - definition: 4 限 メディア情報処理 柱 ・ 6T 5 限 データ構造とアルゴリズム 柱 ・ 6T
      - term: 水曜日
      - definition: 授業なし
      - term: 木曜日
      - definition: 2 限 電子情報基礎数学 礎 ・ 6T
      - term: 金曜日
      - definition: 授業なし
    `);
    await expect(page.getByRole("table")).toBeHidden();
  });

  test("幅 640px 以上では表にし、列の見出しを曜日の名前で読ませる", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto(`/plans/${SAMPLE_PLAN.id}?view=timetable`);
    await expect(
      page.getByRole("columnheader", { name: "月曜日" }),
    ).toBeVisible();
    await expect(
      page.locator("dl").filter({ hasText: NO_LESSONS_LABEL }),
    ).toBeHidden();
  });
});
