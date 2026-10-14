import argparse
import json
from dataclasses import asdict
from enum import Enum
from pathlib import Path

from app.application.ports import TimetableSource
from app.infrastructure.curriculum.ritsumeikan.timetable_pdf import RitsumeikanTimetablePdf


def main() -> None:
    parser = argparse.ArgumentParser(description="授業時間割表の PDF を JSON Lines に変換する")
    parser.add_argument("pdf", type=Path)
    args = parser.parse_args()
    source: TimetableSource = RitsumeikanTimetablePdf(args.pdf)
    for section in source.sections():
        print(json.dumps(asdict(section), ensure_ascii=False, default=_plain))


def _plain(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, frozenset):
        return sorted(value)
    raise TypeError(f"JSON にできません: {type(value).__name__}")


if __name__ == "__main__":
    main()
