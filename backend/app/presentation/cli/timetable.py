import argparse
import json
from dataclasses import asdict
from enum import Enum
from pathlib import Path

from app.infrastructure.curriculum.ritsumeikan.timetable_pdf import parse_timetable


def main() -> None:
    parser = argparse.ArgumentParser(description="授業時間割表の PDF を JSON Lines に変換する")
    parser.add_argument("pdf", type=Path)
    args = parser.parse_args()
    for section in parse_timetable(args.pdf):
        print(json.dumps(asdict(section), ensure_ascii=False, default=_plain))


def _plain(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, frozenset):
        return sorted(value)
    raise TypeError(f"JSON にできません: {type(value).__name__}")


if __name__ == "__main__":
    main()
