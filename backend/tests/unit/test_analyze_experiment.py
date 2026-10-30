import pytest

from app.application.analyze_experiment import (
    TOP_COURSES,
    TOP_OCCUPATIONS,
    AnalyzeExperiment,
    Fate,
    analyze,
    fate_of,
)
from app.application.evaluate_search import EvaluationCase, EvaluationDataset, EvaluationError
from app.application.evaluate_selection import (
    ExpectedCourse,
    Judgment,
    Pick,
    SelectionResult,
    UnlinkedPick,
)
from app.application.run_experiment import Scorecard
from app.domain.recommendation import Relevance
from tests.fakes import courses_ranked_by

CORE, FOUNDATION = Relevance.CORE, Relevance.FOUNDATION
SKILLS = ("甲", "乙", "丙")


def card(
    occupation: str,
    expected: tuple[ExpectedCourse, ...] = (),
    picks: tuple[Pick, ...] = (),
    unlinked: tuple[UnlinkedPick, ...] = (),
    repeat: int = 1,
) -> Scorecard:
    return Scorecard(occupation, repeat, (), SelectionResult(occupation, picks, expected, unlinked))


def unsearched(name: str) -> ExpectedCourse:
    return ExpectedCourse(name, None, False, False)


def skipped(name: str) -> ExpectedCourse:
    return ExpectedCourse(name, None, True, False)


@pytest.mark.parametrize(
    ("course", "reference", "fate"),
    [
        (ExpectedCourse("A", CORE, True, False), frozenset(), Fate.CORE),
        (ExpectedCourse("A", FOUNDATION, True, False), frozenset(), Fate.FOUNDATION),
        (ExpectedCourse("A", None, True, True), frozenset(), Fate.UNLINKED),
        (skipped("A"), frozenset(), Fate.SKIPPED),
        (unsearched("A"), frozenset({"A"}), Fate.READING),
        (unsearched("A"), frozenset({"B"}), Fate.SEARCH),
    ],
)
def test_an_expected_course_is_traced_to_how_it_was_picked_or_the_stage_that_lost_it(
    course: ExpectedCourse, reference: frozenset[str], fate: Fate
) -> None:
    assert fate_of(course, reference) is fate


def test_the_fates_of_every_recommendation_are_counted_together() -> None:
    cards = [
        card("職業", (ExpectedCourse("A", CORE, True, False), unsearched("B"))),
        card("職業", (skipped("A"), unsearched("C")), repeat=2),
    ]

    analysis = analyze(cards, {"職業": frozenset({"B"})})

    assert analysis.fates == {
        Fate.CORE: 1,
        Fate.FOUNDATION: 0,
        Fate.UNLINKED: 0,
        Fate.SKIPPED: 1,
        Fate.READING: 1,
        Fate.SEARCH: 1,
    }


def test_picks_are_tallied_by_where_they_were_placed_and_how_they_were_judged() -> None:
    cards = [
        card(
            "職業",
            picks=(
                Pick("A", CORE, Judgment.EXPECTED),
                Pick("B", CORE, Judgment.UNRELATED),
                Pick("C", FOUNDATION, Judgment.MINORITY),
            ),
            unlinked=(UnlinkedPick("D", "A", Judgment.FOUNDATION),),
        )
    ]

    judgments = analyze(cards, {"職業": frozenset()}).judgments

    assert judgments[Fate.CORE][Judgment.EXPECTED] == 1
    assert judgments[Fate.CORE][Judgment.UNRELATED] == 1
    assert judgments[Fate.FOUNDATION][Judgment.MINORITY] == 1
    assert judgments[Fate.UNLINKED][Judgment.FOUNDATION] == 1
    assert sum(judgments[Fate.UNLINKED].values()) == 1


def test_missed_courses_are_ranked_by_their_losses_with_the_stage_of_each() -> None:
    cards = [
        card("甲職業", (unsearched("A"), skipped("B"))),
        card("乙職業", (unsearched("A"),)),
        card("乙職業", (skipped("A"), ExpectedCourse("C", CORE, True, False)), repeat=2),
    ]

    missed = analyze(cards, {"甲職業": frozenset({"A"}), "乙職業": frozenset()}).missed

    assert [(tally.name, tally.total, tally.occupations) for tally in missed] == [
        ("A", 3, 2),
        ("B", 1, 1),
    ]
    assert missed[0].counts == {Fate.READING: 1, Fate.SEARCH: 1, Fate.SKIPPED: 1}


def test_only_the_most_missed_courses_are_listed() -> None:
    names = [f"科目{number:02}" for number in range(TOP_COURSES + 1)]
    cards = [card("職業", tuple(skipped(name) for name in names))]

    missed = analyze(cards, {"職業": frozenset()}).missed

    assert [tally.name for tally in missed] == names[:TOP_COURSES]


def test_unrelated_picks_leave_out_the_foundations_that_were_dropped_unshown() -> None:
    cards = [
        card(
            "甲職業",
            picks=(Pick("A", FOUNDATION, Judgment.UNRELATED),),
            unlinked=(UnlinkedPick("B", "C", Judgment.UNRELATED),),
        ),
        card("乙職業", picks=(Pick("A", CORE, Judgment.UNRELATED),)),
    ]

    unrelated = analyze(cards, {"甲職業": frozenset(), "乙職業": frozenset()}).unrelated

    assert [(tally.name, tally.occupations) for tally in unrelated] == [("A", 2)]
    assert unrelated[0].counts == {Fate.FOUNDATION: 1, Fate.CORE: 1}


def test_reading_losses_are_ranked_by_occupation_with_the_repeats_they_happened_in() -> None:
    occupations = [f"職業{number}" for number in range(TOP_OCCUPATIONS + 1)]
    cards = [
        card(occupation, (unsearched("A"),), repeat=repeat)
        for occupation in occupations
        for repeat in (1, 2)
    ] + [card(occupations[-1], (unsearched("B"), unsearched("A")), repeat=3)]

    losses = analyze(cards, {occupation: frozenset({"A", "B"}) for occupation in occupations})

    first = losses.reading_losses[0]
    assert (first.occupation, first.total, first.repeats) == (occupations[-1], 4, (1, 2, 3))
    assert list(first.courses.items()) == [("A", 3), ("B", 1)]
    assert len(losses.reading_losses) == TOP_OCCUPATIONS


def test_an_expected_course_missing_from_the_database_is_refused_not_counted_as_a_search_loss() -> (
    None
):
    _, search = courses_ranked_by({"A": 0.9})
    dataset = EvaluationDataset(2026, "情", (EvaluationCase("職業", SKILLS, ("B",)),))

    with pytest.raises(EvaluationError, match="候補に無い科目名があります: B"):
        AnalyzeExperiment(search, 2).run(dataset, [card("職業", (unsearched("B"),))])


def test_the_reference_is_the_search_with_the_handwritten_skills_cut_at_the_candidate_limit() -> (
    None
):
    _, search = courses_ranked_by({"A": 0.9, "B": 0.8, "C": 0.7})
    dataset = EvaluationDataset(2026, "情", (EvaluationCase("職業", SKILLS, ("B", "C")),))

    analysis = AnalyzeExperiment(search, 2).run(
        dataset, [card("職業", (unsearched("B"), unsearched("C")))]
    )

    assert (analysis.fates[Fate.READING], analysis.fates[Fate.SEARCH]) == (1, 1)
    assert [(tally.name, tally.counts) for tally in analysis.missed] == [
        ("B", {Fate.READING: 1}),
        ("C", {Fate.SEARCH: 1}),
    ]
