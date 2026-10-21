import argparse
import json
import sys
from dataclasses import asdict

from app.application.ports import ListingConflictError, SyllabusSource
from app.infrastructure.scrapers.ritsumeikan.detail import SyllabusFormatError
from app.infrastructure.scrapers.ritsumeikan.listing import ListingFormatError
from app.infrastructure.scrapers.ritsumeikan.store import RawStore
from app.infrastructure.scrapers.ritsumeikan.stored import StoredSyllabi
from app.presentation.cli.options import add_raw_store_options


def main() -> None:
    parser = argparse.ArgumentParser(description="保存済みの詳細ページを解析して表示する")
    add_raw_store_options(parser)
    parser.add_argument("codes", nargs="*", help="授業コード。省略時は保存済みを全て検査する")
    args = parser.parse_args()

    store = RawStore(args.root, args.year)
    source: SyllabusSource = StoredSyllabi(store)
    try:
        _show(store, source, args.codes)
    except ListingFormatError as error:
        sys.exit(f"検索結果のページを読めません: {error}")


def _show(store: RawStore, source: SyllabusSource, codes: list[str]) -> None:
    if codes:
        for code in codes:
            try:
                syllabus = source.syllabus(code)
            except ListingConflictError as error:
                print(error)
                continue
            print(json.dumps(asdict(syllabus) if syllabus else None, ensure_ascii=False, indent=1))
        return
    failures = []
    saved = store.saved_detail_codes()
    for code in saved:
        try:
            syllabus = source.syllabus(code)
        except SyllabusFormatError as error:
            failures.append(str(error))
            continue
        if syllabus is not None and syllabus.code != code:
            failures.append(f"{code}: 保存名と主コード {syllabus.code} が違う")
    print(f"保存済み {len(saved)} 件、問題 {len(failures)} 件")
    print("\n".join(failures))


if __name__ == "__main__":
    main()
