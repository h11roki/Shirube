from collections.abc import Sequence

import pytest

from app.application.evaluate_search import EvaluationError
from app.application.evaluate_selection import Judgment, Judgments
from app.application.measure_calibration import (
    Layout,
    MeasureCalibration,
    OccupationOdds,
    SelectorTrial,
    Target,
    calibration,
    matched,
)
from app.application.ports import Classification, ClassificationError, CourseOdds
from app.domain.occupation import OccupationProfile
from app.domain.recommendation import CandidateCourse, Relevance
from tests.builders import course_section, syllabus
from tests.fakes import FakeCourseRepository

PROFILE = OccupationProfile("職業", "読んだ職業", None, ("甲", "乙", "丙"))
CORE, FOUNDATION = Relevance.CORE, Relevance.FOUNDATION


class FakeClassifier:
    def __init__(self, failing_call: int | None = None) -> None:
        self.calls: list[list[str]] = []
        self._failing_call = failing_call

    def classify(
        self, profile: OccupationProfile, candidates: Sequence[CandidateCourse]
    ) -> Classification:
        self.calls.append([candidate.syllabus.code for candidate in candidates])
        if len(self.calls) == self._failing_call:
            raise ClassificationError("Jev の答えを読めません", 70)
        return Classification(
            tuple(CourseOdds(candidate.name, 0.5, 0.3, 0.2) for candidate in candidates),
            100 * len(candidates),
        )


def trial(
    candidates: tuple[str, ...],
    picks: tuple[tuple[str, Relevance], ...] = (),
    occupation: str = "職業",
) -> SelectorTrial:
    return SelectorTrial(occupation, PROFILE, candidates, picks)


def judged(by_course: dict[tuple[str, str], Judgment]) -> Judgments:
    return Judgments(frozenset(course for _, course in by_course), by_course)


def measure(classifier: FakeClassifier) -> MeasureCalibration:
    repository = FakeCourseRepository(
        (course_section("1"), course_section("2")), (syllabus("1"), syllabus("2"))
    )
    return MeasureCalibration(repository, classifier)


@pytest.mark.parametrize(
    ("layout", "calls"),
    [(Layout.GROUPED, [["1", "2"]]), (Layout.SEPARATE, [["1"], ["2"]])],
)
def test_the_candidates_go_to_the_classifier_together_or_one_by_one(
    layout: Layout, calls: list[list[str]]
) -> None:
    classifier = FakeClassifier()

    [(measured_layout, measured)] = measure(classifier).odds(
        2026, "情", [trial(("科目1", "科目2"))], [layout]
    )

    assert measured_layout is layout
    assert classifier.calls == calls
    assert [odds.name for odds in measured.odds] == ["科目1", "科目2"]
    assert measured.input_tokens == 200


def test_a_candidate_without_the_judges_material_is_refused_before_any_call() -> None:
    classifier = FakeClassifier()

    with pytest.raises(EvaluationError, match="判定の資料に無い候補があります: 科目9"):
        measure(classifier).odds(2026, "情", [trial(("科目1", "科目9"))], [Layout.GROUPED])
    assert classifier.calls == []


def occupation_odds(*odds: CourseOdds, occupation: str = "職業") -> OccupationOdds:
    return OccupationOdds(occupation, odds, 0)


def test_calibration_compares_each_band_of_probability_with_how_often_it_hit() -> None:
    measured = [occupation_odds(CourseOdds("A", 0.9, 0.0, 0.1), CourseOdds("B", 0.95, 0.0, 0.05))]
    judgments = judged({("職業", "A"): Judgment.EXPECTED, ("職業", "B"): Judgment.FOUNDATION})

    measured_core = calibration(measured, judgments, Target.CORE)

    [band] = measured_core.bins
    assert (band.low, band.high, band.count) == (0.9, 1.0, 2)
    assert band.mean_probability == pytest.approx(0.925)
    assert band.hit_rate == pytest.approx(0.5)
    assert measured_core.ece == pytest.approx(0.425)
    assert measured_core.brier == pytest.approx((0.1**2 + 0.95**2) / 2)


def test_relevance_adds_core_and_foundation_and_hits_anything_with_a_vote() -> None:
    measured = [occupation_odds(CourseOdds("A", 0.1, 0.2, 0.7), CourseOdds("B", 0.0, 0.0, 1.0))]
    judgments = judged({("職業", "A"): Judgment.MINORITY})

    measured_relevance = calibration(measured, judgments, Target.RELEVANT)

    assert [(band.low, band.hit_rate) for band in measured_relevance.bins] == [
        (0.0, 0.0),
        (0.3, 1.0),
    ]


def test_matched_picks_as_many_as_the_selector_did_by_each_probability() -> None:
    trials = [
        trial(("A", "B", "C"), (("B", CORE), ("C", FOUNDATION))),
        trial(("D",), (("D", CORE),), occupation="測っていない職業"),
    ]
    measured = [
        occupation_odds(
            CourseOdds("A", 0.6, 0.3, 0.1),
            CourseOdds("B", 0.1, 0.1, 0.8),
            CourseOdds("C", 0.2, 0.5, 0.3),
        )
    ]
    judgments = judged(
        {
            ("職業", "A"): Judgment.EXPECTED,
            ("職業", "C"): Judgment.FOUNDATION,
        }
    )

    compared = matched(trials, measured, judgments)

    assert compared.occupations == 1
    assert compared.selector.picked == compared.classifier.picked == 2
    assert (compared.selector.unrelated, compared.classifier.unrelated) == (1, 0)
    assert (compared.selector.expected_picked, compared.classifier.expected_picked) == (0, 1)
    assert compared.selector.expected == compared.classifier.expected == 1
    assert compared.selector.cores == compared.classifier.cores == 1
    assert (compared.selector.expected_cores, compared.classifier.expected_cores) == (0, 1)


def test_both_layouts_come_out_as_one_stream_grouped_first() -> None:
    classifier = FakeClassifier()

    measured = list(
        measure(classifier).odds(
            2026,
            "情",
            [trial(("科目1",)), trial(("科目2",), occupation="別の職業")],
            [Layout.GROUPED, Layout.SEPARATE],
        )
    )

    assert [(layout, each.occupation) for layout, each in measured] == [
        (Layout.GROUPED, "職業"),
        (Layout.GROUPED, "別の職業"),
        (Layout.SEPARATE, "職業"),
        (Layout.SEPARATE, "別の職業"),
    ]


def test_a_failed_call_still_counts_the_tokens_jev_billed_for_it() -> None:
    classifier = FakeClassifier(failing_call=2)
    measuring = measure(classifier)
    outcomes = measuring.odds(2026, "情", [trial(("科目1", "科目2"))], [Layout.SEPARATE])

    with pytest.raises(ClassificationError):
        list(outcomes)
    assert measuring.spent_tokens == 100 + 70


def test_matched_breaks_ties_by_name_not_by_the_search_order() -> None:
    trials = [trial(("B", "A"), (("B", FOUNDATION),))]
    measured = [occupation_odds(CourseOdds("B", 0.2, 0.3, 0.5), CourseOdds("A", 0.2, 0.3, 0.5))]
    judgments = judged({("職業", "A"): Judgment.EXPECTED})

    compared = matched(trials, measured, judgments)

    assert compared.classifier.expected_picked == 1
