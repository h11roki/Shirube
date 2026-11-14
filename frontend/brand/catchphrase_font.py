import hashlib
import re
import sys
import urllib.request
from io import BytesIO
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

FRONTEND = Path(__file__).parent.parent
SITE = FRONTEND / "src" / "lib" / "site.ts"
FONTS = FRONTEND / "src" / "fonts"
OUTPUT = FONTS / "catchphrase.woff2"
LICENSE = FONTS / "OFL.txt"
SOURCE = (
    "https://raw.githubusercontent.com/google/fonts/"
    "d0b2d1307ad5d6b579d627a6e5abd25952484b96/ofl/shipporimincho/"
)
FONT_FILE = "ShipporiMincho-ExtraBold.ttf"
LICENSE_FILE = "OFL.txt"
SHA256 = {
    FONT_FILE: "bdb787644b4b347e9a7efdd576f0d16ee4528cc9b5c86d23e06fa1a14ae0444c",
    LICENSE_FILE: "41fba056279be5f45ff9a99e44b7b53897b42732f5806d8e666e0ab49ac6bd38",
}
REBUILD = "uv run python ../frontend/brand/catchphrase_font.py で作り直してください"


def catchphrase_characters() -> set[str]:
    match = re.search(r"export const CATCHPHRASE = \[(.*?)\];", SITE.read_text(), re.DOTALL)
    if match is None:
        raise SystemExit(f"CATCHPHRASE が {SITE} に見つかりません")
    return set("".join(re.findall(r'"([^"]*)"', match.group(1))))


def fetch(name: str) -> bytes:
    with urllib.request.urlopen(SOURCE + name, timeout=60) as response:
        body: bytes = response.read()
    if hashlib.sha256(body).hexdigest() != SHA256[name]:
        raise SystemExit(f"{name} の SHA-256 が固定した値と違います")
    return body


def build() -> None:
    font = TTFont(BytesIO(fetch(FONT_FILE)))
    license_text = fetch(LICENSE_FILE)
    options = subset.Options()
    options.name_IDs = ["*"]
    subsetter = subset.Subsetter(options)
    subsetter.populate(text="".join(sorted(catchphrase_characters())))
    subsetter.subset(font)
    font.flavor = "woff2"
    FONTS.mkdir(exist_ok=True)
    font.save(OUTPUT)
    LICENSE.write_bytes(license_text)
    print(f"{OUTPUT.relative_to(FRONTEND)}: {OUTPUT.stat().st_size} bytes")


def check() -> None:
    if hashlib.sha256(LICENSE.read_bytes()).hexdigest() != SHA256[LICENSE_FILE]:
        raise SystemExit(f"{LICENSE.relative_to(FRONTEND)} が固定した OFL と違います。{REBUILD}")
    expected = catchphrase_characters()
    actual = {chr(code) for code in TTFont(OUTPUT).getBestCmap()}
    if actual != expected:
        missing = "".join(sorted(expected - actual))
        extra = "".join(sorted(actual - expected))
        raise SystemExit(
            f"{OUTPUT.relative_to(FRONTEND)} の字が CATCHPHRASE と違います"
            f"(足りない字: {missing or 'なし'}、余る字: {extra or 'なし'})。{REBUILD}"
        )
    print(f"{OUTPUT.relative_to(FRONTEND)} は CATCHPHRASE の {len(expected)} 字とちょうど同じです")


if __name__ == "__main__":
    if sys.argv[1:] == ["--check"]:
        check()
    else:
        build()
