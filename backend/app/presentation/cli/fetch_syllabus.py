import argparse
import json
import logging
from pathlib import Path

from app.application.fetch_syllabus import FetchSyllabus
from app.infrastructure.scrapers.ritsumeikan.portal import SyllabusPortal
from app.infrastructure.scrapers.ritsumeikan.store import RawStore

DEFAULT_ROOT = Path("data/raw")


def main() -> None:
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--year", type=int, default=2026)
    shared.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser = argparse.ArgumentParser(description="シラバスの一覧と詳細を取得して保存する")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "listings", parents=[shared], help="学期・曜日・時限ごとの検索結果を保存する"
    )
    details = commands.add_parser(
        "details", parents=[shared], help="授業コードごとの詳細ページを保存する"
    )
    details.add_argument("--codes-from", type=Path, required=True, help="時間割表の JSON Lines")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    with SyllabusPortal(args.year) as portal:
        fetch = FetchSyllabus(portal, RawStore(args.root, args.year))
        if args.command == "listings":
            fetch.listings()
            return
        codes = _codes_in(args.codes_from)
        missing = fetch.details(codes)
        print(f"対象 {len(codes)} 件、見つからない {len(missing)} 件: {' '.join(missing)}")


def _codes_in(path: Path) -> list[str]:
    seen: dict[str, None] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            seen.setdefault(json.loads(line)["code"], None)
    return list(seen)


if __name__ == "__main__":
    main()
