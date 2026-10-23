import pytest

from app.presentation.composition import load_settings


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
