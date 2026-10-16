from app.domain.occupation import OccupationProfile
from app.domain.recommendation import Recommendation, RecommendedCourse, Relevance
from app.presentation.cli.recommend import render


def test_render_lists_the_profile_and_the_courses_by_relevance() -> None:
    profile = OccupationProfile(
        "コンサルタント", "IT コンサルタント", "IT 寄りと解釈した", ("甲", "乙", "丙")
    )
    recommendation = Recommendation(
        profile,
        (
            RecommendedCourse("科目B", "10001", Relevance.CORE, "理由B"),
            RecommendedCourse("科目A", "10000", Relevance.FOUNDATION, "理由A"),
        ),
        30,
    )

    assert render(recommendation) == (
        "職業: コンサルタント → IT コンサルタント\n"
        "前提: IT 寄りと解釈した\n"
        "スキル: 甲 / 乙 / 丙\n"
        "中心 1 科目\n"
        "  科目B: 理由B\n"
        "土台 1 科目\n"
        "  科目A: 理由A\n"
        "検索の上位 30 件から選んだ"
    )
