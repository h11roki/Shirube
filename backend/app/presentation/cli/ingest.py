import argparse
import logging
from pathlib import Path

from sqlalchemy import create_engine

from app.application.ingest_courses import IngestCourses
from app.infrastructure.curriculum.ritsumeikan.timetable_pdf import RitsumeikanTimetablePdf
from app.infrastructure.db.courses import SqlCourseRepository
from app.infrastructure.scrapers.ritsumeikan.store import RawStore
from app.infrastructure.scrapers.ritsumeikan.stored import StoredSyllabi
from app.presentation.cli.raw_options import add_raw_store_options
from app.settings import Settings


def main() -> None:
    parser = argparse.ArgumentParser(description="時間割表と保存済みシラバスを DB に取り込む")
    add_raw_store_options(parser)
    parser.add_argument("timetable", type=Path, help="授業時間割表の PDF")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    ingest = IngestCourses(
        RitsumeikanTimetablePdf(args.timetable),
        StoredSyllabi(RawStore(args.root, args.year)),
        SqlCourseRepository(create_engine(Settings().database_url)),
    )
    report = ingest.run(args.year)
    print(
        f"時間割表 {report.sections} 行、シラバス {report.syllabi} 件、"
        f"シラバス無し {len(report.codes_without_syllabus)} 件: "
        f"{' '.join(report.codes_without_syllabus)}"
    )


if __name__ == "__main__":
    main()
