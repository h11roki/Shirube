from io import BytesIO
from pathlib import Path

from PIL import Image
from playwright.sync_api import Page, sync_playwright

BRAND = Path(__file__).parent
APP = BRAND.parent / "src" / "app"
FAVICON_SIZE = 32


def shoot(page: Page, template: str, width: int, height: int) -> bytes:
    page.set_viewport_size({"width": width, "height": height})
    page.goto((BRAND / template).as_uri())
    page.evaluate("document.fonts.ready")
    return page.screenshot()


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        (APP / "opengraph-image.png").write_bytes(shoot(page, "opengraph-image.html", 1200, 630))
        (APP / "apple-icon.png").write_bytes(shoot(page, "icon.html", 180, 180))
        favicon = shoot(page, "icon.html", FAVICON_SIZE, FAVICON_SIZE)
        browser.close()
    Image.open(BytesIO(favicon)).convert("RGBA").save(
        APP / "favicon.ico", format="ICO", sizes=[(FAVICON_SIZE, FAVICON_SIZE)]
    )


if __name__ == "__main__":
    main()
