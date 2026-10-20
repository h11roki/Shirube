import argparse

import pytest

from app.presentation.cli.options import add_occupation_argument
from app.presentation.schemas.plans import MAX_NAME_LENGTH


def parser() -> argparse.ArgumentParser:
    built = argparse.ArgumentParser()
    add_occupation_argument(built)
    return built


def test_the_occupation_is_trimmed_and_must_be_one_short_line() -> None:
    assert parser().parse_args([" データサイエンティスト "]).occupation == "データサイエンティスト"
    for text in ("データ\nサイエンティスト", "  ", "職" * (MAX_NAME_LENGTH + 1)):
        with pytest.raises(SystemExit):
            parser().parse_args([text])
