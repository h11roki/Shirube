from collections.abc import Sequence

from app.domain.occupation import OccupationProfile
from app.domain.recommendation import CourseChoice, Relevance

RELEVANCE_LABELS = {Relevance.CORE: "中心", Relevance.FOUNDATION: "土台"}
SEARCH_MODES = {True: "スキルごと", False: "クエリ 1 つ"}


def with_prerequisite(name: str, prerequisite_for: str | None) -> str:
    return name if prerequisite_for is None else f"{name}(→ {prerequisite_for})"


def profile_lines(profile: OccupationProfile) -> list[str]:
    return [
        f"職業: {profile.occupation} → {profile.interpretation}",
        *([f"前提: {profile.assumption}"] if profile.assumption is not None else []),
        f"スキル: {' / '.join(profile.skills)}",
    ]


def unlinked_lines(unlinked: Sequence[CourseChoice]) -> list[str]:
    if not unlinked:
        return []
    names = "、".join(
        with_prerequisite(choice.name, choice.prerequisite_for) for choice in unlinked
    )
    return [f"中心につながらず外した土台: {names}"]
