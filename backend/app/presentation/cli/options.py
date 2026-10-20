import argparse
from pathlib import Path

from app.domain.occupation import is_single_line
from app.settings import CurriculumSettings

DEFAULT_DEPARTMENT = "情"
DEFAULT_ROOT = Path("data/raw")


def _occupation(text: str) -> str:
    occupation = text.strip()
    if not is_single_line(occupation):
        raise argparse.ArgumentTypeError(f"職業名は空でない 1 行にしてください: {text!r}")
    return occupation


def add_occupation_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("occupation", type=_occupation)


def add_year_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--year", type=int, default=CurriculumSettings().curriculum_year)


def add_department_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--department", default=DEFAULT_DEPARTMENT)


def add_raw_store_options(parser: argparse.ArgumentParser) -> None:
    add_year_option(parser)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
