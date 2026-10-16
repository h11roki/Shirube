import pytest

from app.domain.occupation import OccupationProfile, OccupationProfileError


def test_query_joins_the_interpretation_and_the_skills() -> None:
    profile = OccupationProfile(
        "コンサルタント",
        "IT コンサルタント",
        "情報系の学生に多い IT コンサルタントと解釈した",
        ("業務分析", "システム設計", "プロジェクト管理"),
    )

    assert profile.query == "IT コンサルタント\n業務分析\nシステム設計\nプロジェクト管理"


@pytest.mark.parametrize(
    ("interpretation", "assumption", "skills", "message"),
    [
        ("  ", None, ("甲", "乙", "丙"), "解釈した職業名が空です"),
        ("職業", " ", ("甲", "乙", "丙"), "前提が空です"),
        ("職業", None, ("甲", "乙"), "スキルは空でないものを 3〜6 個"),
        ("職業", None, tuple("甲乙丙丁戊己庚"), "スキルは空でないものを 3〜6 個"),
        ("職業", None, ("甲", "乙", ""), "スキルは空でないものを 3〜6 個"),
    ],
    ids=["blank-interpretation", "blank-assumption", "two-skills", "seven-skills", "blank-skill"],
)
def test_profile_without_an_interpretation_or_with_wrong_skills_is_rejected(
    interpretation: str, assumption: str | None, skills: tuple[str, ...], message: str
) -> None:
    with pytest.raises(OccupationProfileError, match=message):
        OccupationProfile("職業", interpretation, assumption, skills)


def test_profile_accepts_three_to_six_skills_and_no_assumption() -> None:
    for count in (3, 6):
        skills = tuple(f"スキル{number}" for number in range(count))

        assert OccupationProfile("職業", "職業", None, skills).skills == skills
