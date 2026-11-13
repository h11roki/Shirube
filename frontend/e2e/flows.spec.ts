import type { Locator, Page } from "@playwright/test";

import type {
  OfferedCourse,
  PlacedCourse,
  Plan,
  Relevance,
  Weekday,
} from "@/lib/api/client";
import { MAX_FIXED_COURSES } from "@/lib/fixed-courses";
import {
  ARRIVALS_HINT,
  CANCEL_LABEL,
  CONFIRM_DELETE_LABEL,
  CREATE_PLAN_LABEL,
  DELETE_PLAN_LABEL,
  NO_LESSONS_LABEL,
  OCCUPATION_LABEL,
  REBUILD_LABEL,
  REBUILD_ON_FORM_LABEL,
  REBUILD_SUBMIT_LABEL,
  RELEVANCE_DESCRIPTIONS,
  RELEVANCE_LABELS,
  SAME_OCCUPATION_NOTE,
  TRANSFER_HINT,
  TRANSFER_LABEL,
  answeredLabel,
  arrivalsLabel,
  assumptionLabel,
  backPlace,
  deletePlanLabel,
  deletedPlanLabel,
  dropFixedLabel,
  fixedCoursesSummary,
  hopPlace,
  markTakenLabel,
  matchCountLabel,
  readAsLabel,
  readingLabel,
  stationsAway,
  takenCoursesSummary,
  unmarkTakenLabel,
} from "@/lib/labels";
import { POLL_INTERVAL_MS } from "@/lib/polling";
import { semesterKey, transferRoutes } from "@/lib/roadmap";
import { SAMPLE_PLAN } from "@/lib/sample-plan";
import { LOGIN_PATH } from "@/lib/site";

import {
  CLASS_CHOICES,
  FAILED_PLAN,
  type FinishedPlan,
  OFFERED_COURSES,
  PLAN_LIST,
  READING,
  READING_PLAN,
  REREAD_PLAN,
  RUNNING_PLAN,
  TAKEN_COURSES,
  asFailed,
  asRunning,
  enlargeText,
  expect,
  fontsReady,
  planApi,
  signIn,
  test,
  withSemesterCourses,
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

function markedTaken(plan: FinishedPlan): Plan {
  const rearranged = withSemesterCourses(plan, 0, (courses) =>
    courses.filter((course) => course.name !== TAKEN.name),
  );
  return {
    ...rearranged,
    result: {
      ...rearranged.result,
      taken: [TAKEN],
      offered_earlier: [TAKEN.name],
    },
  };
}

const MARKED_PLAN = markedTaken(SAMPLE_PLAN);

function lesson(
  name: string,
  relevance: Relevance,
  room: string | null,
  weekday: Weekday,
  period: number,
): PlacedCourse {
  return {
    ...SAMPLE_PLAN.result.semesters[0].courses[0],
    name,
    relevance,
    section_code: name,
    slots: [{ weekday, period }],
    room,
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
              lesson("信号処理", "core", "Ｃ３０２", "mon", 2),
              {
                ...lesson("電磁気学", "foundation", "情処演P33", "tue", 1),
                class_confirmed: false,
              },
              lesson("回路理論", "core", null, "tue", 3),
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

test.describe("乗換の欄", () => {
  const MOVED_FROM = 1;
  const moved = SAMPLE_PLAN.result.semesters[MOVED_FROM].courses.find(
    (course) => course.relevance === "foundation",
  );
  if (!moved) {
    throw new Error("見本の道標の 2 学期目に礎が無い");
  }
  const TRANSFER_PLAN = withSemesterCourses(
    withSemesterCourses(SAMPLE_PLAN, MOVED_FROM, (courses) =>
      courses.filter((course) => course !== moved),
    ),
    MOVED_FROM + 1,
    (courses) => [...courses, moved],
  );
  const routes = transferRoutes(TRANSFER_PLAN.result.semesters);
  const transfer = [...routes.departures.values()].find(
    (each) => each.to.station < each.from.station,
  );
  if (!transfer) {
    throw new Error("前の駅の柱へ乗り換える礎が無い");
  }
  const departureOf = (page: Page): Locator =>
    ticketOf(page, transfer.from.name).getByRole("button", {
      name: new RegExp(`^${TRANSFER_LABEL}`),
    });

  function ticketOf(page: Page, name: string): Locator {
    return page.locator("article").filter({ has: nameOf(page, name) });
  }

  function nameOf(page: Page, name: string): Locator {
    return page.getByRole("heading", { name, exact: true });
  }

  for (const width of [NARROW_WIDTH, WIDE_WIDTH]) {
    test(`幅 ${width}px で、礎の乗換の欄を押すと柱の切符へ移って授業名にフォーカスし、戻るで乗換の欄に戻る`, async ({
      page,
      api,
    }) => {
      await page.setViewportSize({ width, height: 800 });
      api.answer({ [planApi(TRANSFER_PLAN)]: TRANSFER_PLAN });
      await page.goto(`/plans/${TRANSFER_PLAN.id}`);
      const departure = departureOf(page);
      await expect(departure).toContainText(transfer.to.name);
      await expect(departure).toContainText(
        `${hopPlace(transfer.to)} ${stationsAway(transfer.from.station, transfer.to.station)}`,
      );
      await fontsReady(page);
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth - innerWidth,
        ),
      ).toBeLessThanOrEqual(0);
      await expect(departure).toHaveAccessibleDescription(TRANSFER_HINT);
      await expect(
        page.getByText(
          `${RELEVANCE_LABELS.foundation}、${RELEVANCE_DESCRIPTIONS.foundation}`,
          { exact: true },
        ),
      ).toBeVisible();
      await departure.click();
      await expect(nameOf(page, transfer.to.name)).toBeFocused();
      await expect(nameOf(page, transfer.to.name)).toBeInViewport();
      const back = page.getByRole("button", {
        name: `${transfer.from.name}${backPlace(transfer.from)}`,
      });
      await expect(back).toBeInViewport();
      await back.click();
      await expect(departure).toBeFocused();
      await expect(back).toHaveCount(0);
    });
  }

  test("ログイン前のトップの見本の道標にも、柱と礎の凡例と乗換の欄の一言が出る", async ({
    page,
  }) => {
    await page.context().clearCookies();
    await page.goto("/");
    await expect(
      page.getByText(
        `${RELEVANCE_LABELS.core}、${RELEVANCE_DESCRIPTIONS.core}`,
        { exact: true },
      ),
    ).toBeVisible();
    await expect(page.getByText(TRANSFER_HINT).first()).toBeVisible();
  });

  test("礎の切符に触れるかフォーカスすると、つながる柱の切符に輪を付ける", async ({
    page,
    api,
  }) => {
    api.answer({ [planApi(TRANSFER_PLAN)]: TRANSFER_PLAN });
    await page.goto(`/plans/${TRANSFER_PLAN.id}`);
    const pillar = ticketOf(page, transfer.to.name);
    await expect(pillar).not.toHaveClass(/ring-route/);
    await ticketOf(page, transfer.from.name).hover();
    await expect(pillar).toHaveClass(/ring-route/);
    await page.mouse.move(0, 0);
    await expect(pillar).not.toHaveClass(/ring-route/);
    await departureOf(page).focus();
    await expect(pillar).toHaveClass(/ring-route/);
  });

  test("柱の乗り入れの欄に礎が並び、押すと礎の切符へ移る", async ({
    page,
    api,
  }) => {
    api.answer({ [planApi(TRANSFER_PLAN)]: TRANSFER_PLAN });
    await page.goto(`/plans/${TRANSFER_PLAN.id}`);
    const pillar = ticketOf(page, transfer.to.name);
    await expect(pillar).toContainText(
      arrivalsLabel(routes.arrivals.get(transfer.to.name)?.length ?? 0),
    );
    const arrival = pillar
      .getByRole("button")
      .filter({ hasText: transfer.from.name });
    await expect(arrival).toHaveAccessibleDescription(ARRIVALS_HINT);
    await arrival.click();
    await expect(nameOf(page, transfer.from.name)).toBeFocused();
    await expect(
      page.getByRole("button", {
        name: `${transfer.to.name}${backPlace(transfer.to)}`,
      }),
    ).toBeVisible();
  });

  test("時間割帳で、別の学期の柱へ乗り換えると、その学期に替えて柱の授業名にフォーカスする", async ({
    page,
    api,
  }) => {
    api.answer({ [planApi(TRANSFER_PLAN)]: TRANSFER_PLAN });
    await page.goto(
      `/plans/${TRANSFER_PLAN.id}?view=timetable&semester=${semesterKey(transfer.from.semester)}`,
    );
    const entries = await page.evaluate(() => history.length);
    await departureOf(page).click();
    await expect(nameOf(page, transfer.to.name)).toBeFocused();
    await expect(page).toHaveURL(
      new RegExp(`semester=${semesterKey(transfer.to.semester)}`),
    );
    expect(await page.evaluate(() => history.length)).toBe(entries);
  });

  test("道標が変わると、着いた切符の戻る道を外す", async ({ page, api }) => {
    const asked = {
      ...TRANSFER_PLAN,
      result: { ...TRANSFER_PLAN.result, offered_earlier: [TAKEN.name] },
    };
    api.answer({ [planApi(asked)]: asked });
    api.respond("PUT", takenApi(TAKEN.name), { json: markedTaken(asked) });
    await page.goto(`/plans/${asked.id}`);
    await departureOf(page).click();
    const back = page.getByRole("button", {
      name: `${transfer.from.name}${backPlace(transfer.from)}`,
    });
    await expect(back).toBeVisible();
    await page
      .getByRole("button", { name: markTakenLabel(TAKEN.name) })
      .click();
    await expect(
      page.getByRole("button", { name: unmarkTakenLabel(TAKEN.name) }),
    ).toBeVisible();
    await expect(back).toHaveCount(0);
  });
});

test.describe("道標を作る", () => {
  test("ログインしていないとき、ヘッダーの道標を作るを押すと、ログインのページへ移る", async ({
    page,
  }) => {
    await page.context().clearCookies();
    await page.goto("/");
    const link = page
      .getByRole("banner")
      .getByRole("link", { name: CREATE_PLAN_LABEL });
    await expect(link).toHaveAttribute("href", LOGIN_PATH);
    await link.click();
    await expect(page).toHaveURL(LOGIN_PATH);
    await expect(
      page.getByRole("button", { name: "Google でログイン" }),
    ).toBeVisible();
  });

  test("ログインしていないとき、無いページの道標を作るもログインのページを指す", async ({
    page,
  }) => {
    await page.context().clearCookies();
    await page.goto("/no-such-station");
    await expect(
      page.getByRole("main").getByRole("link", { name: CREATE_PLAN_LABEL }),
    ).toHaveAttribute("href", LOGIN_PATH);
  });

  test("ログイン済みでログインのページを開くと、入力の画面へ移る", async ({
    page,
    api,
  }) => {
    api.answer({
      "/api/class-choices": CLASS_CHOICES,
      "/api/offered-courses": OFFERED_COURSES,
      "/api/taken-courses": TAKEN_COURSES,
    });
    await page.goto(LOGIN_PATH);
    await expect(page).toHaveURL("/");
    await expect(
      page.getByRole("button", { name: CREATE_PLAN_LABEL }),
    ).toBeEnabled();
    await expect(
      page.getByText(takenCoursesSummary(TAKEN_COURSES.names.length)),
    ).toBeVisible();
  });

  test("作って結果の画面に移ったあと、入力の画面に戻ると、職業名が空でもう一度作れる", async ({
    page,
    api,
  }) => {
    api.answer({
      "/api/class-choices": CLASS_CHOICES,
      "/api/offered-courses": OFFERED_COURSES,
      "/api/taken-courses": TAKEN_COURSES,
      [planApi(SAMPLE_PLAN)]: SAMPLE_PLAN,
    });
    api.respond("POST", "/api/plans", { status: 202, json: SAMPLE_PLAN });
    await page.goto("/");
    await page
      .getByLabel("なりたい職業")
      .fill(SAMPLE_PLAN.conditions.occupation);
    await page.getByRole("button", { name: CREATE_PLAN_LABEL }).click();
    await expect(page).toHaveURL(`/plans/${SAMPLE_PLAN.id}`);
    await expect(
      page.getByRole("button", { name: DELETE_PLAN_LABEL }),
    ).toBeVisible();
    const link = page
      .getByRole("banner")
      .getByRole("link", { name: CREATE_PLAN_LABEL });
    await expect(link).toHaveAttribute("href", "/");
    await link.click();
    await expect(page).toHaveURL("/");
    await expect(page.getByLabel("なりたい職業")).toHaveValue("");
    await expect(
      page.getByRole("button", { name: CREATE_PLAN_LABEL }),
    ).toBeEnabled();
  });
});

test.describe("先に入れる授業", () => {
  test("名前で絞って選んだ授業を送り、選んだ授業から外すと欄の見出しにフォーカスを戻す", async ({
    page,
    api,
  }) => {
    const [kept, dropped] = OFFERED_COURSES.courses.filter((course) =>
      course.name.includes("回路"),
    );
    api.answer({
      "/api/class-choices": CLASS_CHOICES,
      "/api/offered-courses": OFFERED_COURSES,
      "/api/taken-courses": TAKEN_COURSES,
      [planApi(SAMPLE_PLAN)]: SAMPLE_PLAN,
    });
    api.respond("POST", "/api/plans", { status: 202, json: SAMPLE_PLAN });
    await page.goto("/");
    await page
      .getByLabel("なりたい職業")
      .fill(SAMPLE_PLAN.conditions.occupation);
    await page.getByText(fixedCoursesSummary(0)).click();
    await page.getByLabel("授業名で絞る").fill("回路");
    await page.getByLabel("授業名で絞る").press("Enter");
    await expect(page.getByText(matchCountLabel(2))).toBeVisible();
    await page.getByRole("checkbox", { name: kept.name, exact: true }).check();
    await page
      .getByRole("checkbox", { name: dropped.name, exact: true })
      .check();
    await page
      .getByRole("button", { name: dropFixedLabel(dropped.name) })
      .click();
    await expect(page.getByText(fixedCoursesSummary(1))).toBeFocused();
    await expect(
      page.getByRole("checkbox", { name: dropped.name, exact: true }),
    ).not.toBeChecked();
    const posted = page.waitForRequest(
      (request) =>
        request.method() === "POST" &&
        new URL(request.url()).pathname === "/api/plans",
    );
    await page.getByRole("button", { name: CREATE_PLAN_LABEL }).click();
    expect((await posted).postDataJSON()).toMatchObject({
      fixed_courses: [kept.name],
    });
    await expect(
      page.getByRole("button", { name: DELETE_PLAN_LABEL }),
    ).toBeVisible();
  });

  test("回生を変えても欄は開いたままで、一覧に無くなった授業は、変えた先の一覧で選び直すと選んだ並びから外れる", async ({
    page,
    api,
  }) => {
    const [firstGradeOnly, , secondGradeOnly] = OFFERED_COURSES.courses;
    const firstGrade = { term: "spring", courses: [firstGradeOnly] };
    const secondGrade = { term: "spring", courses: [secondGradeOnly] };
    api.answer({
      "/api/class-choices": CLASS_CHOICES,
      "/api/taken-courses": TAKEN_COURSES,
    });
    api.respond(
      "GET",
      "/api/offered-courses",
      { json: firstGrade },
      { json: secondGrade },
      { json: firstGrade },
    );
    await page.goto("/");
    await page.getByText(fixedCoursesSummary(0)).click();
    await page
      .getByRole("checkbox", { name: firstGradeOnly.name, exact: true })
      .check();
    await page.getByLabel("いまの回生").selectOption("2");
    await page
      .getByRole("checkbox", { name: secondGradeOnly.name, exact: true })
      .check();
    await expect(page.getByText(fixedCoursesSummary(1))).toBeVisible();
    await page.getByLabel("いまの回生").selectOption("1");
    await expect(page.getByText(fixedCoursesSummary(0))).toBeVisible();
    await expect(
      page.getByRole("checkbox", { name: firstGradeOnly.name, exact: true }),
    ).not.toBeChecked();
  });

  test(`${MAX_FIXED_COURSES} 科目を選ぶと、ほかの授業は選べない`, async ({
    page,
    api,
  }) => {
    const courses: OfferedCourse[] = Array.from(
      { length: MAX_FIXED_COURSES + 1 },
      (_, index) => ({
        name: `授業 ${String(index + 1).padStart(2, "0")}`,
        credits: 2,
        semesters: [{ grade: 1, term: "spring" }],
      }),
    );
    api.answer({
      "/api/class-choices": CLASS_CHOICES,
      "/api/offered-courses": { term: "spring", courses },
      "/api/taken-courses": TAKEN_COURSES,
    });
    await page.goto("/");
    await page.getByText(fixedCoursesSummary(0)).click();
    for (const course of courses.slice(0, MAX_FIXED_COURSES)) {
      await page
        .getByRole("checkbox", { name: course.name, exact: true })
        .check();
    }
    await expect(
      page.getByText(fixedCoursesSummary(MAX_FIXED_COURSES)),
    ).toBeVisible();
    await expect(
      page.getByRole("checkbox", { name: courses.at(-1)?.name, exact: true }),
    ).toBeDisabled();
    await page
      .getByRole("button", { name: dropFixedLabel(courses[0].name) })
      .click();
    await expect(
      page.getByRole("checkbox", { name: courses.at(-1)?.name, exact: true }),
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

  for (const width of [320, 375, 1280]) {
    test(`幅 ${width}px で、月〜金と時限の表にし、時限の時刻と、授業の柱か礎と教室を出す`, async ({
      page,
    }) => {
      await page.setViewportSize({ width, height: 900 });
      await page.goto(`/plans/${WEEK_PLAN.id}?view=timetable`);
      const table = page.getByRole("table");
      for (const day of ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日"]) {
        await expect(
          table.getByRole("columnheader", { name: day }),
        ).toBeVisible();
      }
      await expect(table.getByRole("rowheader").first()).toHaveAccessibleName(
        "1 限 9:00 から 10:35",
      );
      for (const [name, note] of [
        ["信号処理", "柱 教室 C302"],
        ["電磁気学", "礎 教室 情処演P33クラス未確定"],
        ["回路理論", "柱"],
      ]) {
        await expect(
          table.getByRole("cell").filter({ hasText: name }),
        ).toHaveText(`${name}${note}`);
      }
    });
  }

  test("ブラウザの文字を 200% にすると、幅 320px と 375px の時間割帳は曜日ごとの一覧にする", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 320, height: 900 });
    await page.goto(`/plans/${WEEK_PLAN.id}?view=timetable`);
    await enlargeText(page);
    const list = page.locator("dl").filter({ hasText: NO_LESSONS_LABEL });
    for (const width of [320, 375]) {
      await page.setViewportSize({ width, height: 900 });
      await expect(list).toBeVisible();
      await expect(page.getByRole("table")).toBeHidden();
    }
    for (const width of [640, 1280]) {
      await page.setViewportSize({ width, height: 900 });
      const table = page.getByRole("table");
      await expect(table).toBeVisible();
      await expect(list).toBeHidden();
      await fontsReady(page);
      expect(
        await table.evaluate((grid) =>
          [...grid.querySelectorAll("td > span")]
            .filter((note) => note.scrollWidth > note.clientWidth + 1)
            .map((note) => note.textContent),
        ),
        "マスからはみ出した授業",
      ).toEqual([]);
    }
  });

  test("道のりの駅の時間割は、枠が狭い幅 320px では曜日ごとの一覧にし、曜日を略さずに時限の時刻とともに読ませる", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 320, height: 900 });
    await page.goto(`/plans/${WEEK_PLAN.id}`);
    await page
      .getByRole("button", { name: /この学期の時間割を開く/ })
      .first()
      .click();
    await expect(page.locator("dl").filter({ hasText: NO_LESSONS_LABEL }))
      .toMatchAriaSnapshot(`
      - term: 月曜日
      - definition: 2 限 10:45 から 12:20 信号処理 柱 教室 C302
      - term: 火曜日
      - definition: 1 限 9:00 から 10:35 電磁気学 礎 教室 情処演P33 クラス未確定 3 限 13:10 から 14:45 回路理論 柱
      - term: 水曜日
      - definition: 授業なし
      - term: 木曜日
      - definition: 授業なし
      - term: 金曜日
      - definition: 授業なし
    `);
    await expect(page.getByRole("table")).toBeHidden();
  });

  test("道のりの駅の時間割は、枠に余裕のある幅 375px では表にする", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 375, height: 900 });
    await page.goto(`/plans/${WEEK_PLAN.id}`);
    await page
      .getByRole("button", { name: /この学期の時間割を開く/ })
      .first()
      .click();
    await expect(
      page.getByRole("table").getByRole("columnheader", { name: "月曜日" }),
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
  const nav = banner.getByRole("link", { name: CREATE_PLAN_LABEL });
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

test.describe("読み替えの知らせ", () => {
  test("作成中に、広く読み替えた職業として作っていることと前提を、読み上げの枠に出す", async ({
    page,
    api,
  }) => {
    api.answer({ [planApi(READING_PLAN)]: READING_PLAN });
    await page.goto(`/plans/${READING_PLAN.id}`);
    const notice = page
      .locator('[aria-live="polite"]')
      .filter({ hasText: readingLabel(READING.interpretation) });
    await expect(notice).toBeVisible();
    await expect(notice).toContainText(assumptionLabel(READING.assumption));
  });

  test("完成の画面では、行き先を入力した職業名にし、読み替えた職業を板の上に添える", async ({
    page,
    api,
  }) => {
    api.answer({ [planApi(REREAD_PLAN)]: REREAD_PLAN });
    await page.goto(`/plans/${REREAD_PLAN.id}`);
    await expect(
      page.getByRole("heading", {
        level: 1,
        name: `${READING.occupation}への道標`,
      }),
    ).toBeAttached();
    await expect(
      page.getByText(`${READING.occupation}行`, { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", {
        name: `${READING.occupation}へ`,
        exact: true,
      }),
    ).toBeVisible();
    await expect(
      page
        .getByRole("navigation", { name: "路線図" })
        .getByRole("button", { name: READING.occupation, exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText(`${READING.interpretation}行`, { exact: true }),
    ).toHaveCount(0);
    await expect(
      page.getByRole("heading", {
        name: `${READING.interpretation}へ`,
        exact: true,
      }),
    ).toHaveCount(0);
    await expect(
      page.getByText(readAsLabel(READING.interpretation)),
    ).toBeVisible();
    await expect(
      page.getByText(`入力した職業 ${READING.occupation}`),
    ).toHaveCount(0);
  });

  test("作成中でも、前提の無い読み取りは知らせない", async ({ page, api }) => {
    const plain = {
      ...READING_PLAN,
      reading: {
        ...READING,
        interpretation: READING.occupation,
        assumption: null,
      },
    };
    api.answer({ [planApi(plain)]: plain });
    await page.goto(`/plans/${plain.id}`);
    await expect(
      page.getByRole("heading", { name: /道標を作っています/ }),
    ).toBeVisible();
    await expect(page.getByText(/として作っています/)).toHaveCount(0);
  });

  test("完成の画面で別の職業名で作り直すと、同じ職業名は断り、ほかの条件はそのままで職業名だけ替えて送り、新しい道標へ移る", async ({
    page,
    api,
  }) => {
    const rebuilt = Promise.withResolvers<void>();
    api.answer({ [planApi(REREAD_PLAN)]: REREAD_PLAN });
    api.respond("GET", planApi(SAMPLE_PLAN), {
      json: SAMPLE_PLAN,
      until: rebuilt.promise,
    });
    api.respond("POST", "/api/plans", { status: 202, json: SAMPLE_PLAN });
    await page.goto(`/plans/${REREAD_PLAN.id}`);
    await page.getByRole("button", { name: REBUILD_LABEL }).click();
    const field = page.getByRole("textbox", { name: OCCUPATION_LABEL });
    await expect(field).toBeFocused();
    await field.fill(` ${READING.occupation} `);
    await page.getByRole("button", { name: REBUILD_SUBMIT_LABEL }).click();
    await expect(
      page.getByRole("alert").filter({ hasText: SAME_OCCUPATION_NOTE }),
    ).toBeVisible();
    await expect(field).toBeFocused();
    await expect(field).toHaveAttribute("aria-invalid", "true");
    await expect(field).toHaveAccessibleDescription(
      new RegExp(SAME_OCCUPATION_NOTE),
    );
    await field.fill(SAMPLE_PLAN.conditions.occupation);
    const posted = page.waitForRequest(
      (request) =>
        request.method() === "POST" &&
        new URL(request.url()).pathname === "/api/plans",
    );
    await page.getByRole("button", { name: REBUILD_SUBMIT_LABEL }).click();
    const { conditions } = REREAD_PLAN;
    expect((await posted).postDataJSON()).toEqual({
      occupation: SAMPLE_PLAN.conditions.occupation,
      grade: conditions.grade,
      term: conditions.term,
      department: conditions.department,
      chosen_classes: conditions.chosen_classes,
      fixed_courses: conditions.fixed_courses,
    });
    await expect(page).toHaveURL(`/plans/${SAMPLE_PLAN.id}`);
    await expect(page.getByRole("form", { name: REBUILD_LABEL })).toHaveCount(
      0,
    );
    await expect(
      page.getByRole("button", { name: DELETE_PLAN_LABEL }),
    ).toHaveCount(0);
    rebuilt.resolve();
    await expect(
      page.getByRole("navigation", { name: "路線図" }),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: REBUILD_LABEL })).toHaveCount(
      0,
    );
  });

  test("断られたら API の文をその場に出し、条件で断られたら入力の画面への導線も出し、やめるで閉じると押したボタンにフォーカスを戻す", async ({
    page,
    api,
  }) => {
    api.answer({ [planApi(REREAD_PLAN)]: REREAD_PLAN });
    api.respond(
      "POST",
      "/api/plans",
      { status: 429, json: { detail: "今日はもう道標を作れません" } },
      { status: 422, json: { detail: "選べないクラスです" } },
    );
    await page.goto(`/plans/${REREAD_PLAN.id}`);
    const opener = page.getByRole("button", { name: REBUILD_LABEL });
    await opener.click();
    await page
      .getByRole("textbox", { name: OCCUPATION_LABEL })
      .fill(SAMPLE_PLAN.conditions.occupation);
    await page.getByRole("button", { name: REBUILD_SUBMIT_LABEL }).click();
    await expect(
      page.getByRole("alert").filter({ hasText: "今日はもう道標を作れません" }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: REBUILD_ON_FORM_LABEL }),
    ).toHaveCount(0);
    await page.getByRole("button", { name: REBUILD_SUBMIT_LABEL }).click();
    await expect(
      page.getByRole("alert").filter({ hasText: "選べないクラスです" }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: REBUILD_ON_FORM_LABEL }),
    ).toHaveAttribute("href", "/");
    await expect(page).toHaveURL(`/plans/${REREAD_PLAN.id}`);
    await page
      .getByRole("form", { name: REBUILD_LABEL })
      .getByRole("button", { name: CANCEL_LABEL })
      .click();
    await expect(opener).toBeFocused();
    await opener.click();
    await expect(
      page.getByRole("textbox", { name: OCCUPATION_LABEL }),
    ).toHaveValue("");
    await expect(
      page.getByRole("alert").filter({ hasText: "選べないクラスです" }),
    ).toHaveCount(0);
  });
});
