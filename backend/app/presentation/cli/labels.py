from app.domain.recommendation import Relevance

RELEVANCE_LABELS = {Relevance.CORE: "中心", Relevance.FOUNDATION: "土台"}


def with_prerequisite(name: str, prerequisite_for: str | None) -> str:
    return name if prerequisite_for is None else f"{name}(→ {prerequisite_for})"
