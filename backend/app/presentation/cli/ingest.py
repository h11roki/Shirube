import argparse
import sys
from pathlib import Path

from sqlalchemy import create_engine

from app.application.ingest_courses import IngestError, IngestSyllabi, IngestTimetable
from app.infrastructure.curriculum.ritsumeikan.timetable_pdf import (
    RitsumeikanTimetablePdf,
    TimetableFormatError,
)
from app.infrastructure.db.courses import SqlCourseRepository
from app.infrastructure.scrapers.ritsumeikan.detail import SyllabusFormatError
from app.infrastructure.scrapers.ritsumeikan.store import RawStore
from app.infrastructure.scrapers.ritsumeikan.stored import StoredSyllabi
from app.presentation.cli.options import add_raw_store_options, add_year_option
from app.settings import Settings


def main() -> None:
    parser = argparse.ArgumentParser(description="時間割表とシラバスを年度単位で DB に入れ替える")
    commands = parser.add_subparsers(dest="command", required=True)
    timetable = commands.add_parser("timetable", help="その年度の時間割表を全て取り込む")
    add_year_option(timetable)
    timetable.add_argument("pdfs", type=Path, nargs="+", help="授業時間割表の PDF")
    syllabi = commands.add_parser("syllabi", help="保存済みのシラバスを全て取り込む")
    add_raw_store_options(syllabi)
    args = parser.parse_args()

    engine = create_engine(Settings().database_url)
    repository = SqlCourseRepository(engine)
    try:
        if args.command == "timetable":
            sources = [RitsumeikanTimetablePdf(pdf) for pdf in args.pdfs]
            print(f"時間割表 {IngestTimetable(sources, repository).run(args.year)} 行")
            return
        source = StoredSyllabi(RawStore(args.root, args.year))
        report = IngestSyllabi(source, repository).run(args.year)
        print(
            f"シラバス {report.pages} ページ、時間割表でシラバス無し "
            f"{len(report.codes_without_syllabus)} 件: {' '.join(report.codes_without_syllabus)}"
        )
    except (IngestError, TimetableFormatError, SyllabusFormatError) as error:
        sys.exit(f"取り込みを止めました: {error}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
