import argparse
from pathlib import Path

from app.settings import DEFAULT_CURRICULUM_YEAR

DEFAULT_DEPARTMENT = "情"
DEFAULT_ROOT = Path("data/raw")


def add_year_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--year", type=int, default=DEFAULT_CURRICULUM_YEAR)


def add_department_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--department", default=DEFAULT_DEPARTMENT)


def add_raw_store_options(parser: argparse.ArgumentParser) -> None:
    add_year_option(parser)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
