import pytest

from app.domain.occupation import (
    OccupationProfile,
    OccupationProfileError,
    is_readable,
    search_query,
)


def test_query_joins_the_interpretation_and_the_skills() -> None:
    profile = OccupationProfile(
        "コンサルタント",
        "IT コンサルタント",
        "情報系の学生に多い IT コンサルタントと解釈した",
        ("業務分析", "システム設計", "プロジェクト管理"),
    )

    assert profile.query == "IT コンサルタント\n業務分析\nシステム設計\nプロジェクト管理"


@pytest.mark.parametrize(
    ("occupation", "interpretation", "assumption", "skills", "message"),
    [
        (" ", "職業", None, ("甲", "乙", "丙"), "職業名が空です"),
        ("職業", "  ", None, ("甲", "乙", "丙"), "解釈した職業名は空でない 1 行に"),
        ("職業", "職業\n補足", None, ("甲", "乙", "丙"), "解釈した職業名は空でない 1 行に"),
        ("職業", "職業", " ", ("甲", "乙", "丙"), "前提が空です"),
        ("職業", "職業", None, ("甲", "乙"), "スキルは 3〜6 個に"),
        ("職業", "職業", None, tuple("甲乙丙丁戊己庚"), "スキルは 3〜6 個に"),
        ("職業", "職業", None, ("甲", "乙", ""), "スキルは空でない 1 行に"),
        ("職業", "職業", None, ("甲", "乙", "丙\n丁"), "スキルは空でない 1 行に"),
        ("職業", "職業", None, ("甲", "乙", "丙\u2028丁"), "スキルは空でない 1 行に"),
        ("職業", "職業", None, ("甲", "乙", "甲"), "スキルが重複しています"),
        ("職業", "職業", None, ("甲", "乙", " 甲"), "スキルが重複しています"),
    ],
    ids=[
        "blank-occupation",
        "blank-interpretation",
        "multiline-interpretation",
        "blank-assumption",
        "two-skills",
        "seven-skills",
        "blank-skill",
        "multiline-skill",
        "line-separator-in-skill",
        "duplicated-skill",
        "duplicated-skill-with-padding",
    ],
)
def test_profile_that_would_break_the_query_is_rejected(
    occupation: str,
    interpretation: str,
    assumption: str | None,
    skills: tuple[str, ...],
    message: str,
) -> None:
    with pytest.raises(OccupationProfileError, match=message):
        OccupationProfile(occupation, interpretation, assumption, skills)


def test_search_query_puts_the_occupation_and_each_skill_on_its_own_line() -> None:
    assert search_query("職業", ["甲", "乙"]) == "職業\n甲\n乙"


def test_profile_accepts_three_to_six_skills_and_no_assumption() -> None:
    for count in (3, 6):
        skills = tuple(f"スキル{number}" for number in range(count))

        assert OccupationProfile("職業", "職業", None, skills).skills == skills


@pytest.mark.parametrize(
    ("text", "readable"),
    [
        ("情報科学Ⅱ", True),
        ("C 言語と Python", True),
        ("α-β 法・データ構造(基礎)", True),
        ("Ｗｅｂ の仕組み → 応用", True),
        ("コンピュータグラフィिक्स", False),
        ("데이터 분석", False),
        ("การเขียนโปรแกรม", False),
    ],
)
def test_readable_text_is_japanese_ascii_and_common_symbols(text: str, readable: bool) -> None:
    assert is_readable(text) is readable


def test_a_reading_without_an_assumption_keeps_the_name_the_user_wrote() -> None:
    skills = ("確率統計", "機械学習", "データベース")

    kept = OccupationProfile.read("データサイエンティスト", "データ分析エンジニア", None, skills)
    broadened = OccupationProfile.read("Webエンジニア", "ITエンジニア", "広く読んだ", skills)

    assert kept.interpretation == "データサイエンティスト"
    assert broadened.interpretation == "ITエンジニア"


def test_a_profile_with_unreadable_letters_is_not_readable() -> None:
    profile = OccupationProfile("職業", "職業", None, ("甲", "乙", "ग्राफ"))

    assert profile.readable is False
    assert OccupationProfile("職業", "職業", None, ("甲", "乙", "丙")).readable is True
