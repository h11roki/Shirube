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


def test_the_selection_prompt_setting_replaces_the_built_in_instructions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://shirube:shirube@localhost:1/none")
    monkeypatch.delenv("SELECTION_PROMPT", raising=False)
    prompt = tmp_path / "selection.txt"
    prompt.write_text("試す指示文", encoding="utf-8")

    assert selection_instructions(load_settings()) == INSTRUCTIONS
    assert selection_instructions(load_settings(selection_prompt=str(prompt))) == "試す指示文"


@pytest.mark.parametrize("text", [None, " \n"], ids=["missing", "blank"])
def test_a_selection_prompt_that_is_missing_or_blank_is_refused(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, text: str | None
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://shirube:shirube@localhost:1/none")
    prompt = tmp_path / "selection.txt"
    if text is not None:
        prompt.write_text(text, encoding="utf-8")

    with pytest.raises(SystemExit, match="SELECTION_PROMPT"):
        load_settings(selection_prompt=str(prompt))
