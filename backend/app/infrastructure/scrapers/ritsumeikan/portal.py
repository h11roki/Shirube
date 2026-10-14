import re
import time
from collections.abc import Callable
from types import TracebackType
from typing import Self

from playwright.sync_api import Browser, Page, Playwright, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from app.infrastructure.scrapers.ritsumeikan.listing import (
    ListingRow,
    parse_listing,
    parse_page_count,
)

BASE_URL = "https://syllabus.ritsumei.ac.jp"
HOME_PATH = "/syllabus/s/?language=ja"
USER_AGENT = "shirube/0.1 (+https://github.com/h11roki/Shirube; takahashi.hiroki@baseconnect.in)"
FACULTY = "理工学部"
RESULTS_PER_PAGE = "50"
LOAD_TIMEOUT_MS = 90_000
RESULT_TIMEOUT_MS = 60_000
RETRY_COUNT = 3
RETRY_WAIT_SECONDS = 15.0
RESULT_MARKER = re.compile(r"全\s*\d+\s*件|検索結果が多すぎる")
TOO_MANY_RESULTS = "検索結果が多すぎる"
DETAIL_MARKER = "シラバス情報"


class TooManyResultsError(RuntimeError):
    pass


class SyllabusPortal:
    def __init__(self, year: int, interval_seconds: float = 3.0) -> None:
        self._year = year
        self._interval = interval_seconds
        self._last_request = 0.0
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._page: Page | None = None

    def __enter__(self) -> Self:
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch()
        self._page = self._browser.new_page(user_agent=USER_AGENT, locale="ja-JP")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()

    def search(self, term: str, weekday: str | None, period: int | None) -> list[ListingRow]:
        def run() -> list[ListingRow]:
            page = self._open_home()
            page.get_by_role("combobox", name="学期").click()
            page.get_by_role("option", name=term, exact=True).click()
            groups = page.locator("lightning-checkbox-group")
            if weekday is not None:
                groups.nth(0).get_by_text(f"{weekday}曜日", exact=True).click()
            if period is not None:
                groups.nth(1).get_by_text(str(period), exact=True).click()
            return self._submit(page)

        return self._retry(run)

    def search_code(self, code: str) -> list[ListingRow]:
        def run() -> list[ListingRow]:
            page = self._open_home()
            page.locator("input[name='keyword-search']").fill(code)
            return self._submit(page)

        return self._retry(run)

    def detail_html(self, href: str) -> str:
        def run() -> str:
            page = self._goto(f"{BASE_URL}{href}?language=ja")
            page.get_by_text(DETAIL_MARKER).first.wait_for(timeout=RESULT_TIMEOUT_MS)
            return page.content()

        return self._retry(run)

    def _open_home(self) -> Page:
        page = self._goto(f"{BASE_URL}{HOME_PATH}")
        page.get_by_role("combobox", name="学部・研究科").click()
        page.get_by_role("option", name=FACULTY, exact=True).click()
        page.get_by_role("combobox", name="年度").click()
        page.get_by_role("option", name=str(self._year), exact=True).click()
        page.locator("select[name='results-per-page']").select_option(RESULTS_PER_PAGE)
        return page

    def _submit(self, page: Page) -> list[ListingRow]:
        page.get_by_role("button", name="検索").click()
        marker = page.get_by_text(RESULT_MARKER).first
        marker.wait_for(timeout=RESULT_TIMEOUT_MS)
        if TOO_MANY_RESULTS in marker.inner_text():
            raise TooManyResultsError("検索結果が多すぎるため絞り込みが必要")
        rows = parse_listing(page.content())
        count = parse_page_count(marker.inner_text())
        while count is not None and count.current < count.last:
            self._pause()
            page.get_by_role("button", name="次へ").click()
            shown = re.compile(rf"（\s*{count.current + 1}\s*/\s*{count.last}\s*ページ）")
            page.get_by_text(shown).first.wait_for(timeout=RESULT_TIMEOUT_MS)
            rows.extend(parse_listing(page.content()))
            count = parse_page_count(marker.inner_text())
        return rows

    def _goto(self, url: str) -> Page:
        if self._page is None:
            raise RuntimeError("with 文の中で使う")
        self._pause()
        self._page.goto(url, wait_until="networkidle", timeout=LOAD_TIMEOUT_MS)
        return self._page

    def _pause(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self._interval:
            time.sleep(self._interval - elapsed)
        self._last_request = time.monotonic()

    def _retry[T](self, action: Callable[[], T]) -> T:
        for attempt in range(1, RETRY_COUNT + 1):
            try:
                return action()
            except PlaywrightTimeoutError:
                if attempt == RETRY_COUNT:
                    raise
                time.sleep(RETRY_WAIT_SECONDS * attempt)
        raise AssertionError("unreachable")
