import pytest
from pydantic import SecretStr

from app.application.cached_occupation_analyzer import CachedOccupationAnalyzer
from app.application.ports import OccupationAnalysisError
from app.domain.occupation import OccupationProfile
from app.infrastructure.llm.openai_occupation_analyzer import OpenAIOccupationAnalyzer
from app.presentation.composition import occupation_analyzer
from app.settings import Settings
from tests.fakes import FakeOccupationAnalyzer


def profile(occupation: str) -> OccupationProfile:
    return OccupationProfile(occupation, f"{occupation}の読み", None, ("甲", "乙", "丙"))


PROFILES = {name: profile(name) for name in ("職業A", "職業B", "職業C")}


class FailingFirst(FakeOccupationAnalyzer):
    def analyze(self, occupation: str) -> OccupationProfile:
        if not self.calls:
            self.calls.append(occupation)
            raise OccupationAnalysisError("推薦に使う外部のサービスの呼び出しに失敗しました")
        return super().analyze(occupation)


def test_the_same_occupation_is_read_once_and_remembered() -> None:
    reader = FakeOccupationAnalyzer(PROFILES)
    analyzer = CachedOccupationAnalyzer(reader, 10)

    first = analyzer.analyze("職業A")
    second = analyzer.analyze("職業A")

    assert first == second == PROFILES["職業A"]
    assert reader.calls == ["職業A"]


def test_different_occupations_are_read_separately() -> None:
    reader = FakeOccupationAnalyzer(PROFILES)
    analyzer = CachedOccupationAnalyzer(reader, 10)

    assert analyzer.analyze("職業A") == PROFILES["職業A"]
    assert analyzer.analyze("職業B") == PROFILES["職業B"]
    assert reader.calls == ["職業A", "職業B"]


def test_a_failed_reading_is_not_remembered() -> None:
    reader = FailingFirst(PROFILES)
    analyzer = CachedOccupationAnalyzer(reader, 10)

    with pytest.raises(OccupationAnalysisError):
        analyzer.analyze("職業A")

    assert analyzer.analyze("職業A") == PROFILES["職業A"]
    assert reader.calls == ["職業A", "職業A"]


def test_when_full_the_reading_used_longest_ago_is_forgotten() -> None:
    reader = FakeOccupationAnalyzer(PROFILES)
    analyzer = CachedOccupationAnalyzer(reader, 2)

    analyzer.analyze("職業A")
    analyzer.analyze("職業B")
    analyzer.analyze("職業A")
    analyzer.analyze("職業C")
    analyzer.analyze("職業A")
    analyzer.analyze("職業B")

    assert reader.calls == ["職業A", "職業B", "職業C", "職業B"]


@pytest.mark.parametrize(
    ("size", "kind"),
    [(0, OpenAIOccupationAnalyzer), (500, CachedOccupationAnalyzer)],
    ids=["off", "on"],
)
def test_the_reading_is_remembered_only_when_the_cache_has_room(size: int, kind: type) -> None:
    settings = Settings(
        database_url="postgresql+psycopg://shirube@localhost/shirube",
        openai_api_key=SecretStr("test-key"),
        occupation_reading_cache_size=size,
    )

    assert isinstance(occupation_analyzer(settings), kind)
