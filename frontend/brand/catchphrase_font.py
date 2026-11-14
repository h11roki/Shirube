import hashlib
import json
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
SOURCE = (
    "https://raw.githubusercontent.com/google/fonts/"
    "d0b2d1307ad5d6b579d627a6e5abd25952484b96/ofl/shipporimincho/"
)
FILES = {
    "ShipporiMincho-ExtraBold.ttf": (
        "bdb787644b4b347e9a7efdd576f0d16ee4528cc9b5c86d23e06fa1a14ae0444c"
    ),
    "OFL.txt": "41fba056279be5f45ff9a99e44b7b53897b42732f5806d8e666e0ab49ac6bd38",
}


def catchphrase_characters() -> set[str]:
    match = re.search(r"export const CATCHPHRASE = (\[.*?\]);", SITE.read_text())
    if match is None:
        raise SystemExit(f"CATCHPHRASE が {SITE} に見つかりません")
    return set("".join(json.loads(match.group(1))))


def fetch(name: str) -> bytes:
    with urllib.request.urlopen(SOURCE + name, timeout=60) as response:
        body: bytes = response.read()
    if hashlib.sha256(body).hexdigest() != FILES[name]:
        raise SystemExit(f"{name} の SHA-256 が固定した値と違います")
    return body


def covered_characters(path: Path) -> set[str]:
    return {chr(code) for code in TTFont(path).getBestCmap()}


def build() -> None:
    font = TTFont(BytesIO(fetch("ShipporiMincho-ExtraBold.ttf")))
    subsetter = subset.Subsetter(subset.Options())
    subsetter.populate(text="".join(sorted(catchphrase_characters())))
    subsetter.subset(font)
    FONTS.mkdir(exist_ok=True)
    font.flavor = "woff2"
    font.save(OUTPUT)
    (FONTS / "OFL.txt").write_bytes(fetch("OFL.txt"))
    print(f"{OUTPUT.relative_to(FRONTEND)}: {OUTPUT.stat().st_size} bytes")


def check() -> None:
    expected = catchphrase_characters()
    actual = covered_characters(OUTPUT)
    if actual != expected:
        missing = "".join(sorted(expected - actual))
        extra = "".join(sorted(actual - expected))
        raise SystemExit(
            f"{OUTPUT.relative_to(FRONTEND)} の字が CATCHPHRASE と違います"
            f"(足りない字: {missing or 'なし'}、余る字: {extra or 'なし'})。"
            "uv run python ../frontend/brand/catchphrase_font.py で作り直してください"
        )
    print(f"{OUTPUT.relative_to(FRONTEND)} は CATCHPHRASE の {len(expected)} 字とちょうど同じです")


if __name__ == "__main__":
    if sys.argv[1:] == ["--check"]:
        check()
    else:
        build()
