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
    StoredJudgment,
    cohen_kappa,
    fleiss_kappa,
    judged_reasons,
    sample_reasons,
    verified_judgments,
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


def names(occupations: int) -> list[str]:
    return [f"職業{index}" for index in range(occupations)]


def cases(occupations: int, each: int = 40) -> list[ReasonCase]:
    return [
        case(name, relevance, number)
        for name in names(occupations)
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


def stored(key: str, answer: ReasonGrade = VAGUE, reason: str = "理由") -> StoredJudgment:
    sampled = SampledReason(
        key, Split.TUNE, ReasonCase("職業", "解釈", None, Relevance.CORE, "授業", None, reason)
    )
    votes = (ReasonVote(SPECIFIC, "根拠"), ReasonVote(VAGUE, "根拠"), ReasonVote(ABSENT, "根拠"))
    return StoredJudgment(JudgedReason(sampled, votes), answer)


def test_stored_judgments_that_match_the_samples_are_returned_in_order() -> None:
    judgments = [stored("r001"), stored("r002")]

    verified = verified_judgments([judgment.reason.sample for judgment in judgments], judgments)

    assert verified == [judgment.reason for judgment in judgments]


@pytest.mark.parametrize(
    ("judgments", "message"),
    [
        ([stored("r002"), stored("r001")], "同じ順に並んでいません"),
        ([stored("r001"), stored("r001")], "同じ順に並んでいません"),
        (
            [stored("r001", reason="書き換えた理由"), stored("r002")],
            "r001: 結果から取り直した理由と違います",
        ),
        (
            [stored("r001"), stored("r002", answer=SPECIFIC)],
            "r002: 正解が 3 票の中央値ではありません",
        ),
    ],
    ids=["reordered", "repeated", "reason-edited", "answer-edited"],
)
def test_stored_judgments_that_drifted_from_the_samples_are_refused(
    judgments: list[StoredJudgment], message: str
) -> None:
    samples = [stored("r001").reason.sample, stored("r002").reason.sample]

    with pytest.raises(ReasonJudgingError, match=message):
        verified_judgments(samples, judgments)


def test_the_sample_splits_the_occupations_in_half_and_takes_the_same_counts_from_each() -> None:
    sampled = sample_reasons(cases(6), names(6))

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
    first_half = sample_reasons(cases(6), names(6))[:75]

    assert {reason.split for reason in first_half} == set(Split)
    assert {reason.case.relevance for reason in first_half} == set(Relevance)


def test_the_same_reasons_and_seed_give_the_same_sample() -> None:
    assert sample_reasons(cases(6), names(6)) == sample_reasons(cases(6), names(6))
    assert sample_reasons(cases(6), names(6), seed=1) != sample_reasons(cases(6), names(6))


def test_the_sample_refuses_a_half_without_enough_reasons() -> None:
    with pytest.raises(ReasonJudgingError, match="38 件に足りません: 20 件"):
        sample_reasons(cases(2, each=20), names(2))


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
    first, second = {"r001": ReasonVote(VAGUE, "根拠1")}, {"r001": ReasonVote(VAGUE, "根拠2")}
    wrong = {"r002": ReasonVote(VAGUE, "根拠")}

    with pytest.raises(ReasonJudgingError, match="3 つ目.*足りない: r001、多い: r002"):
        judged_reasons([sample()], [first, second, wrong])


def test_the_same_output_passed_twice_is_refused() -> None:
    output = {"r001": ReasonVote(VAGUE, "根拠")}
    other = {"r001": ReasonVote(VAGUE, "別の根拠")}

    with pytest.raises(ReasonJudgingError, match="同じ判定者の出力が 2 つ以上"):
        judged_reasons([sample()], [output, other, dict(output)])


def test_an_occupation_without_reasons_keeps_the_others_in_the_same_half() -> None:
    def halves(sampled: list[SampledReason]) -> dict[str, Split]:
        return {reason.case.occupation: reason.split for reason in sampled}

    everyone = halves(sample_reasons(cases(8), names(8)))
    failed = [reason for reason in cases(8) if reason.occupation != "職業3"]

    without = halves(sample_reasons(failed, names(8)))

    assert "職業3" not in without
    assert without == {name: split for name, split in everyone.items() if name in without}


def test_a_reason_of_an_occupation_outside_the_split_is_refused() -> None:
    with pytest.raises(ReasonJudgingError, match="分ける職業に無い職業の理由があります: 職業5"):
        sample_reasons(cases(6), names(5))


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


def test_cohen_kappa_removes_the_agreement_expected_by_chance() -> None:
    pairs = [(SPECIFIC, SPECIFIC), (SPECIFIC, VAGUE), (VAGUE, VAGUE), (ABSENT, ABSENT)]

    assert cohen_kappa(pairs) == pytest.approx((0.75 - 0.3125) / (1 - 0.3125))


def test_cohen_kappa_is_undefined_when_both_sides_always_give_the_same_grade() -> None:
    assert cohen_kappa([(VAGUE, VAGUE), (VAGUE, VAGUE)]) is None


def test_cohen_kappa_needs_pairs() -> None:
    with pytest.raises(ReasonJudgingError, match="比べる段の組がありません"):
        cohen_kappa([])
