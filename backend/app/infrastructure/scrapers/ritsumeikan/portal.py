import time
from collections.abc import Callable
from types import TracebackType
from typing import Self

from playwright.sync_api import Browser, Page, Playwright, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from app.application.ports import ListingQuery
from app.infrastructure.scrapers.ritsumeikan.listing import PageCount, parse_page_count
from app.infrastructure.scrapers.ritsumeikan.site import BASE_URL, detail_url

HOME_PATH = "/syllabus/s/?language=ja"
USER_AGENT = "shirube/0.1 (+https://github.com/h11roki/Shirube)"
FACULTY = "理工学部"
TERMS_WITH_SLOTS = ("春学期", "秋学期", "通年")
TERMS_WITHOUT_SLOTS = ("夏期集中", "冬期集中")
WEEKDAYS = ("月", "火", "水", "木", "金", "土", "日")
PERIODS = range(1, 8)
RESULTS_PER_PAGE = "50"
LOAD_TIMEOUT_MS = 90_000
RESULT_TIMEOUT_SECONDS = 60.0
POLL_SECONDS = 0.5
RETRY_COUNT = 3
RETRY_WAIT_SECONDS = 15.0
NO_RESULTS = "一致する情報は見つかりませんでした"
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
        try:
            self._browser = self._playwright.chromium.launch()
            self._page = self._browser.new_page(user_agent=USER_AGENT, locale="ja-JP")
        except Exception:
            self._playwright.stop()
            raise
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

    def listing_queries(self) -> list[ListingQuery]:
        queries = [
            ListingQuery(f"{term}_{weekday}_{period}", term, weekday, period)
            for term in TERMS_WITH_SLOTS
            for weekday in WEEKDAYS
            for period in PERIODS
        ]
        return queries + [ListingQuery(term, term, None, None) for term in TERMS_WITHOUT_SLOTS]

    def listing_pages(self, query: ListingQuery) -> list[str]:
        def run() -> list[str]:
            page = self._open_home()
            page.get_by_role("combobox", name="学期").click()
            page.get_by_role("option", name=query.term, exact=True).click()
            groups = page.locator("lightning-checkbox-group")
            if query.weekday is not None:
                groups.nth(0).get_by_text(f"{query.weekday}曜日", exact=True).click()
            if query.period is not None:
                groups.nth(1).get_by_text(str(query.period), exact=True).click()
            return self._submit(page)

        return self._retry(run)

    def lookup_pages(self, code: str) -> list[str]:
        def run() -> list[str]:
            page = self._open_home()
            page.locator("input[name='keyword-search']").fill(code)
            return self._submit(page)

        return self._retry(run)

    def detail_page(self, href: str) -> str:
        def run() -> str:
            page = self._goto(detail_url(href))
            page.get_by_text(DETAIL_MARKER).first.wait_for(timeout=LOAD_TIMEOUT_MS)
            self._stamp()
            return page.content()

        return self._retry(run)

    def _open_home(self) -> Page:
        page = self._goto(f"{BASE_URL}{HOME_PATH}")
        self._stamp()
        page.get_by_role("combobox", name="学部・研究科").click()
        page.get_by_role("option", name=FACULTY, exact=True).click()
        page.get_by_role("combobox", name="年度").click()
        page.get_by_role("option", name=str(self._year), exact=True).click()
        page.locator("select[name='results-per-page']").select_option(RESULTS_PER_PAGE)
        return page

    def _submit(self, page: Page) -> list[str]:
        self._pause()
        page.get_by_role("button", name="検索").click()
        count = self._wait_for_results(page, 1)
        if count is None:
            return []
        pages = [page.content()]
        while count.current < count.last:
            self._pause()
            page.get_by_role("button", name="次へ").click()
            count = self._wait_for_results(page, count.current + 1) or count
            pages.append(page.content())
        return pages

    def _wait_for_results(self, page: Page, expected_page: int) -> PageCount | None:
        deadline = time.monotonic() + RESULT_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            text = page.locator("body").inner_text()
            count = parse_page_count(text)
            if count is not None and count.current == expected_page:
                self._stamp()
                return count
            if NO_RESULTS in text:
                self._stamp()
                return None
            if TOO_MANY_RESULTS in text:
                raise TooManyResultsError("検索結果が多すぎるため絞り込みが必要")
            time.sleep(POLL_SECONDS)
        raise TimeoutError(f"検索結果の {expected_page} ページ目が表示されない")

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

    def _stamp(self) -> None:
        self._last_request = time.monotonic()

    def _retry[T](self, action: Callable[[], T]) -> T:
        for attempt in range(1, RETRY_COUNT + 1):
            try:
                return action()
            except (PlaywrightTimeoutError, TimeoutError):
                if attempt == RETRY_COUNT:
                    raise
                time.sleep(RETRY_WAIT_SECONDS * attempt)
        raise AssertionError("unreachable")
