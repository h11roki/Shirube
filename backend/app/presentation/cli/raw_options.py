import argparse
from pathlib import Path

DEFAULT_YEAR = 2026
DEFAULT_ROOT = Path("data/raw")


def add_raw_store_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--year", type=int, default=DEFAULT_YEAR)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
