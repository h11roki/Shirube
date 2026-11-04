import pytest

from app.application.reason_judging import (
    PER_SPLIT,
    JudgedReason,
    ReasonCase,
    ReasonGrade,
    ReasonJudgingError,
    ReasonVote,
    SampledReason,
    Split,
    fleiss_kappa,
    judged_reasons,
    sample_reasons,
)
from app.domain.recommendation import Relevance

SPECIFIC, VAGUE, ABSENT = ReasonGrade.SPECIFIC, ReasonGrade.VAGUE, ReasonGrade.ABSENT


def case(occupation: str, relevance: Relevance, number: int) -> ReasonCase:
    return ReasonCase(
        occupation,
        f"{occupation}の解釈",
        None,
        relevance,
        f"授業{number}",
        "柱の授業" if relevance is Relevance.FOUNDATION else None,
        f"{occupation}の授業{number}の理由",
    )


def cases(occupations: int, each: int = 40) -> list[ReasonCase]:
    return [
        case(f"職業{index}", relevance, number)
        for index in range(occupations)
        for relevance in Relevance
        for number in range(each)
    ]


def sample(key: str = "r001") -> SampledReason:
    return SampledReason(key, Split.TUNE, case("職業", Relevance.CORE, 1))


def judged(*grades: ReasonGrade) -> JudgedReason:
    return JudgedReason(sample(), tuple(ReasonVote(grade, "根拠") for grade in grades))


@pytest.mark.parametrize(
    ("grades", "answer"),
    [
        ((SPECIFIC, SPECIFIC, ABSENT), SPECIFIC),
        ((ABSENT, VAGUE, ABSENT), ABSENT),
        ((ABSENT, SPECIFIC, VAGUE), VAGUE),
        ((VAGUE, VAGUE, VAGUE), VAGUE),
    ],
)
def test_the_answer_is_the_middle_of_the_three_votes(
    grades: tuple[ReasonGrade, ...], answer: ReasonGrade
) -> None:
    assert judged(*grades).answer is answer


def test_a_reason_needs_exactly_three_votes() -> None:
    with pytest.raises(ReasonJudgingError, match="票は 3 つ"):
        judged(SPECIFIC, VAGUE)


@pytest.mark.parametrize("why", ["", "あ" * 61])
def test_a_vote_needs_a_short_evidence(why: str) -> None:
    with pytest.raises(ReasonJudgingError, match="根拠は 1〜60 字"):
        ReasonVote(VAGUE, why)


@pytest.mark.parametrize(
    ("relevance", "pillar"), [(Relevance.CORE, "柱の授業"), (Relevance.FOUNDATION, None)]
)
def test_only_a_foundation_names_the_pillar_it_leads_to(
    relevance: Relevance, pillar: str | None
) -> None:
    with pytest.raises(ReasonJudgingError, match="礎にだけ"):
        ReasonCase("職業", "解釈", None, relevance, "授業", pillar, "理由")


def test_the_sample_splits_the_occupations_in_half_and_takes_the_same_counts_from_each() -> None:
    sampled = sample_reasons(cases(6))

    occupations = {
        split: {reason.case.occupation for reason in sampled if reason.split is split}
        for split in Split
    }
    assert len(occupations[Split.TUNE]) == len(occupations[Split.CHECK]) == 3
    assert not occupations[Split.TUNE] & occupations[Split.CHECK]
    for split in Split:
        for relevance, count in PER_SPLIT.items():
            assert (
                sum(
                    1
                    for reason in sampled
                    if reason.split is split and reason.case.relevance is relevance
                )
                == count
            )
    assert [reason.key for reason in sampled] == [f"r{number:03d}" for number in range(1, 151)]
    assert len({reason.case for reason in sampled}) == 150


def test_the_sample_mixes_the_splits_and_kinds_in_its_order() -> None:
    first_half = sample_reasons(cases(6))[:75]

    assert {reason.split for reason in first_half} == set(Split)
    assert {reason.case.relevance for reason in first_half} == set(Relevance)


def test_the_same_reasons_and_seed_give_the_same_sample() -> None:
    assert sample_reasons(cases(6)) == sample_reasons(cases(6))
    assert sample_reasons(cases(6), seed=1) != sample_reasons(cases(6))


def test_the_sample_refuses_a_half_without_enough_reasons() -> None:
    with pytest.raises(ReasonJudgingError, match="38 件に足りません: 20 件"):
        sample_reasons(cases(2, each=20))


def test_votes_are_paired_with_the_sampled_reasons_in_judge_order() -> None:
    reasons = [sample("r001"), sample("r002")]
    outputs = [
        {"r001": ReasonVote(SPECIFIC, f"判定者{judge}"), "r002": ReasonVote(ABSENT, "根拠")}
        for judge in range(3)
    ]

    paired = judged_reasons(reasons, outputs)

    assert [reason.sample.key for reason in paired] == ["r001", "r002"]
    assert [vote.why for vote in paired[0].votes] == ["判定者0", "判定者1", "判定者2"]
    assert [reason.answer for reason in paired] == [SPECIFIC, ABSENT]


def test_votes_from_other_than_three_judges_are_refused() -> None:
    with pytest.raises(ReasonJudgingError, match="3 つ渡してください: 2 つ"):
        judged_reasons([sample()], [{"r001": ReasonVote(VAGUE, "根拠")}] * 2)


def test_an_output_missing_or_adding_a_reason_is_refused() -> None:
    complete = {"r001": ReasonVote(VAGUE, "根拠")}
    wrong = {"r002": ReasonVote(VAGUE, "根拠")}

    with pytest.raises(ReasonJudgingError, match="3 つ目.*足りない: r001、多い: r002"):
        judged_reasons([sample()], [complete, complete, wrong])


def test_fleiss_kappa_is_one_when_the_judges_always_agree() -> None:
    assert fleiss_kappa([[SPECIFIC] * 3, [ABSENT] * 3]) == pytest.approx(1.0)


def test_fleiss_kappa_falls_below_zero_when_the_judges_disagree_more_than_chance() -> None:
    ratings = [[SPECIFIC, SPECIFIC, ABSENT], [ABSENT, ABSENT, SPECIFIC]]

    assert fleiss_kappa(ratings) == pytest.approx(-1 / 3)


def test_fleiss_kappa_is_undefined_when_every_vote_is_the_same_grade() -> None:
    assert fleiss_kappa([[VAGUE] * 3, [VAGUE] * 3]) is None


@pytest.mark.parametrize("ratings", [[], [[VAGUE]], [[VAGUE] * 3, [VAGUE] * 2]])
def test_fleiss_kappa_needs_the_same_two_or_more_votes_for_every_reason(
    ratings: list[list[ReasonGrade]],
) -> None:
    with pytest.raises(ReasonJudgingError, match="同じ数の 2 つ以上の票"):
        fleiss_kappa(ratings)
