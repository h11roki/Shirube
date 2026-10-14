import argparse
import json
from dataclasses import asdict
from pathlib import Path

from app.application.ports import SyllabusSource
from app.infrastructure.scrapers.ritsumeikan.detail import SyllabusFormatError
from app.infrastructure.scrapers.ritsumeikan.store import RawStore
from app.infrastructure.scrapers.ritsumeikan.stored import StoredSyllabi

DEFAULT_ROOT = Path("data/raw")


def main() -> None:
    parser = argparse.ArgumentParser(description="保存済みの詳細ページを解析して表示する")
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("codes", nargs="*", help="授業コード。省略時は保存済みを全て検査する")
    args = parser.parse_args()

    store = RawStore(args.root, args.year)
    source: SyllabusSource = StoredSyllabi(store)
    if args.codes:
        for code in args.codes:
            syllabus = source.syllabus(code)
            print(json.dumps(asdict(syllabus) if syllabus else None, ensure_ascii=False, indent=1))
        return
    failures = []
    codes = store.saved_detail_codes()
    for code in codes:
        try:
            source.syllabus(code)
        except SyllabusFormatError as error:
            failures.append(f"{code}: {error}")
    print(f"保存済み {len(codes)} 件、解析できない {len(failures)} 件")
    print("\n".join(failures))


if __name__ == "__main__":
    main()
