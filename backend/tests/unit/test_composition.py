import pytest

from app.application.search_courses import query_and_skills, whole_query
from app.presentation.composition import load_settings, search_queries


def test_settings_given_by_name_override_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://shirube:shirube@localhost:1/none")
    monkeypatch.setenv("SELECTION_VOTES", "3")
    monkeypatch.delenv("SELECTION_MIN_VOTES", raising=False)
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


def test_a_minimum_over_the_votes_names_both_settings_in_japanese(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://shirube:shirube@localhost:1/none")
    monkeypatch.setenv("SELECTION_MIN_VOTES", "2")

    with pytest.raises(SystemExit) as refusal:
        load_settings(selection_votes="1")

    assert str(refusal.value) == (
        "環境変数か、指定した設定を確かめてください: "
        "設定: SELECTION_MIN_VOTES は SELECTION_VOTES 以下にしてください: 2 > 1"
    )


def test_the_skill_search_setting_chooses_how_the_queries_are_made(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://shirube:shirube@localhost:1/none")
    monkeypatch.delenv("SEARCH_BY_SKILL", raising=False)

    assert search_queries(load_settings()) is query_and_skills
    assert search_queries(load_settings(search_by_skill="false")) is whole_query
