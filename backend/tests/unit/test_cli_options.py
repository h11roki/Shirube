import argparse

import pytest

from app.presentation.cli.options import add_occupation_argument


def parser() -> argparse.ArgumentParser:
    built = argparse.ArgumentParser()
    add_occupation_argument(built)
    return built


def test_the_occupation_is_trimmed_and_must_be_one_line() -> None:
    assert parser().parse_args([" データサイエンティスト "]).occupation == "データサイエンティスト"
    for text in ("データ\nサイエンティスト", "  "):
        with pytest.raises(SystemExit):
            parser().parse_args([text])
