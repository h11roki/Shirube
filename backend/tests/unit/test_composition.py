from pathlib import Path

import pytest

from app.application.search_courses import query_and_skills, whole_query
from app.infrastructure.llm.openai_course_selector import INSTRUCTIONS
from app.presentation.composition import load_settings, search_queries, selection_instructions


def test_settings_given_by_name_override_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://shirube:shirube@localhost:1/none")
    monkeypatch.setenv("SELECTION_VOTES", "3")
    monkeypatch.setenv("SELECTION_CANDIDATE_LIMIT", "20")

    settings = load_settings(selection_votes="1")

    assert (settings.selection_votes, settings.selection_candidate_limit) == (1, 20)
    assert load_settings().selection_votes == 3


def test_a_setting_given_out_of_range_names_it_without_blaming_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://shirube:shirube@localhost:1/none")

    with pytest.raises(
        SystemExit, match="環境変数か、指定した設定を確かめてください: SELECTION_VOTES"
    ):
        load_settings(selection_votes="9")


def test_the_skill_search_setting_chooses_how_the_queries_are_made(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://shirube:shirube@localhost:1/none")
    monkeypatch.delenv("SEARCH_BY_SKILL", raising=False)

    assert search_queries(load_settings()) is query_and_skills
    assert search_queries(load_settings(search_by_skill="false")) is whole_query


def test_the_selection_prompt_is_read_once_without_the_surrounding_blanks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://shirube:shirube@localhost:1/none")
    monkeypatch.delenv("SELECTION_PROMPT", raising=False)
    prompt = tmp_path / "selection.txt"
    prompt.write_text("試す指示文\n", encoding="utf-8")

    settings = load_settings(selection_prompt=str(prompt))
    prompt.write_text("書き換えた指示文", encoding="utf-8")

    assert selection_instructions(settings) == "試す指示文"
    assert selection_instructions(load_settings()) == INSTRUCTIONS


@pytest.mark.parametrize("kind", ["missing", "blank", "directory"])
def test_a_selection_prompt_that_cannot_be_used_is_refused(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, kind: str
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://shirube:shirube@localhost:1/none")
    monkeypatch.delenv("SELECTION_PROMPT", raising=False)
    prompt = tmp_path / "selection.txt"
    if kind == "blank":
        prompt.write_text(" \n", encoding="utf-8")
    if kind == "directory":
        prompt.mkdir()

    with pytest.raises(SystemExit, match="SELECTION_PROMPT"):
        load_settings(selection_prompt=str(prompt))


def test_the_selection_prompt_is_refused_in_the_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://shirube:shirube@localhost:1/none")
    prompt = tmp_path / "selection.txt"
    prompt.write_text("試す指示文", encoding="utf-8")
    monkeypatch.setenv("SELECTION_PROMPT", str(prompt))

    with pytest.raises(SystemExit, match="SELECTION_PROMPT は環境変数に書かず"):
        load_settings()
