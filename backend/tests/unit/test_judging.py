import re
from dataclasses import replace

import pytest

from app.application.judging import (
    EVIDENCE_LENGTH,
    JUDGES,
    OVERVIEW_LENGTH,
    CourseMaterial,
    JudgedCourse,
    JudgeOutput,
    JudgingError,
    JudgingMaterials,
    Vote,
    combine,
    decide,
    expected_courses,
)
from app.domain.recommendation import Relevance
from app.domain.syllabus import Session, Syllabus
from tests.builders import course_section, syllabus
from tests.fakes import FakeCourseRepository

CORE, FOUNDATION = Relevance.CORE, Relevance.FOUNDATION
PARTS = (("科目A", "科目B"), ("科目C", "科目D"))
PAGES = {"科目A": "1", "科目B": "2", "科目C": "3", "科目D": "4"}


def judged(
    name: str, *labels: tuple[str, Relevance], decision: Relevance | None = None
) -> JudgedCourse:
    return JudgedCourse(
        name, PAGES.get(name, "9"), {judge: Vote(label, judge) for judge, label in labels}, decision
    )


def test_expected_courses_are_majority_cores_or_core_decisions_ranked_by_votes_then_name() -> None:
    courses = [
        judged("科目F", ("engineer", CORE), ("professor", CORE)),
        judged("科目C", ("engineer", CORE), ("professor", FOUNDATION), decision=CORE),
        judged("科目D", ("student", CORE), decision=FOUNDATION),
        judged("科目E", ("engineer", FOUNDATION), ("professor", FOUNDATION)),
        judged("科目B", ("engineer", CORE), ("student", CORE)),
        judged("科目A", ("engineer", CORE), ("professor", CORE), ("student", CORE)),
    ]

    expected = expected_courses(courses)

    assert list(expected.items()) == [
        ("科目A", "professor"),
        ("科目B", "student"),
        ("科目F", "professor"),
        ("科目C", "engineer"),
    ]


def test_a_course_with_a_single_core_vote_waits_for_a_decision() -> None:
    single = judged("科目A", ("engineer", CORE), ("professor", FOUNDATION))

    assert single.undecided
    assert not replace(single, decision=FOUNDATION).undecided
    assert not judged("科目A", ("engineer", CORE), ("student", CORE)).undecided


def test_a_vote_from_an_unknown_judge_is_refused() -> None:
    with pytest.raises(JudgingError, match="科目A: 知らない判定者の票があります: teacher"):
        judged("科目A", ("teacher", CORE), ("student", CORE))


@pytest.mark.parametrize(
    "labels",
    [(("engineer", FOUNDATION),), (("engineer", CORE), ("student", CORE))],
    ids=["no-core", "two-cores"],
)
def test_a_decision_belongs_only_to_a_course_with_a_single_core_vote(
    labels: tuple[tuple[str, Relevance], ...],
) -> None:
    with pytest.raises(JudgingError, match="決定は中心が 1 票だけの科目にだけ付けます"):
        judged("科目A", *labels, decision=CORE)


@pytest.mark.parametrize("evidence", ["", "あ" * (EVIDENCE_LENGTH + 1)], ids=["empty", "long"])
def test_evidence_is_a_short_summary(evidence: str) -> None:
    with pytest.raises(JudgingError, match="根拠は"):
        Vote(CORE, evidence)


def output(judge: str, votes: dict[str, dict[str, Relevance]]) -> JudgeOutput:
    return JudgeOutput(
        judge,
        {
            occupation: {course: Vote(label, "根拠") for course, label in courses.items()}
            for occupation, courses in votes.items()
        },
    )


FIRST = {"職業": {"科目A": CORE}}
SECOND = {"職業": {"科目C": FOUNDATION}}


def every_judge(votes: dict[str, dict[str, Relevance]]) -> list[JudgeOutput]:
    return [output(judge, votes) for judge in JUDGES]


def test_combine_gathers_both_halves_of_every_judge_by_occupation() -> None:
    combined = combine([every_judge(FIRST), every_judge(SECOND)], PARTS, PAGES, ["職業"])

    assert combined == {
        "職業": [
            JudgedCourse("科目A", "1", {judge: Vote(CORE, "根拠") for judge in JUDGES}),
            JudgedCourse("科目C", "3", {judge: Vote(FOUNDATION, "根拠") for judge in JUDGES}),
        ]
    }
    assert list(combined["職業"][0].votes) == list(JUDGES)


def test_a_judge_may_find_nothing_in_a_half() -> None:
    second = [*every_judge(SECOND)[:2], output("student", {"職業": {}})]

    combined = combine([every_judge(FIRST), second], PARTS, PAGES, ["職業"])

    assert list(combined["職業"][1].votes) == ["engineer", "professor"]


@pytest.mark.parametrize(
    ("halves", "message"),
    [
        ([every_judge(FIRST)], "判定者の出力を科目の 2 つの組に分けて"),
        (
            [[*every_judge(FIRST), output("guest", FIRST)], every_judge(SECOND)],
            "1 つ目の組の判定者が 1 体ずつそろっていません",
        ),
        (
            [every_judge(FIRST), [*every_judge(SECOND)[:2], output("engineer", SECOND)]],
            "2 つ目の組の判定者が 1 体ずつそろっていません",
        ),
        (
            [every_judge(FIRST), every_judge(SECOND)[:2]],
            "2 つ目の組の判定者が 1 体ずつそろっていません",
        ),
        (
            [every_judge({"別の職業": {"科目A": CORE}}), every_judge(SECOND)],
            re.escape("判定する職業がそろっていません(足りない職業: 職業、多い職業: 別の職業。"),
        ),
        (
            [every_judge({"職業": {"科目A": CORE, "科目C": CORE}}), every_judge(SECOND)],
            "1 つ目の組に無い科目に票があります: 科目C",
        ),
    ],
    ids=["one-half", "unknown-judge", "same-judge", "missing-judge", "other-occupation", "outside"],
)
def test_combine_refuses_outputs_that_do_not_cover_every_judge_once_per_half(
    halves: list[list[JudgeOutput]], message: str
) -> None:
    with pytest.raises(JudgingError, match=message):
        combine(halves, PARTS, PAGES, ["職業"])


def test_decide_settles_only_courses_with_a_single_core_vote() -> None:
    single = judged("科目A", ("engineer", CORE), ("professor", FOUNDATION))
    majority = judged("科目B", ("engineer", CORE), ("student", CORE))

    decided = decide({"職業": [single, majority]}, {"職業": {"科目A": FOUNDATION}})

    assert decided == {"職業": [replace(single, decision=FOUNDATION), majority]}
    with pytest.raises(JudgingError, match="中心が 1 票だけではない科目に決定があります: 科目B"):
        decide({"職業": [single, majority]}, {"職業": {"科目B": CORE}})


def test_materials_take_the_department_class_and_an_excerpt_of_its_syllabus() -> None:
    sections = (
        replace(course_section("1"), name="科目A", departments=None),
        replace(course_section("2"), name="科目A", departments=frozenset({"情"})),
        replace(course_section("3"), name="科目B", departments=None),
        replace(course_section("4"), name="科目C", departments=frozenset({"電"})),
    )
    long_page = replace(
        syllabus("2"),
        overview="あ" * (OVERVIEW_LENGTH + 10),
        sessions=(
            Session("1", "導入", ""),
            Session("2", " ", ""),
            Session("3", "まとめ\n 演習", ""),
        ),
    )
    repository = FakeCourseRepository(
        sections, (syllabus("1"), long_page, syllabus("3"), syllabus("4"))
    )

    materials = JudgingMaterials(repository).courses(2026, "情")

    assert materials == [
        CourseMaterial(
            "科目A",
            "基礎専・専門",
            (1, 2, 3, 4),
            "2",
            "あ" * OVERVIEW_LENGTH,
            "目標",
            "導入、まとめ 演習",
        ),
        CourseMaterial(
            "科目B", "基礎専・専門", (1, 2, 3, 4), "3", "概要 段落", "目標", "導入、展開"
        ),
    ]


class MissingPages(FakeCourseRepository):
    def syllabi_of(self, year: int, primary_codes: object) -> dict[str, Syllabus]:
        return {}


def test_materials_refuse_a_course_whose_syllabus_is_missing() -> None:
    repository = MissingPages((replace(course_section("1"), name="科目A"),), (syllabus("1"),))

    with pytest.raises(JudgingError, match="シラバスが DB にありません: 科目A"):
        JudgingMaterials(repository).courses(2026, "情")


def test_materials_refuse_a_department_without_candidates() -> None:
    repository = FakeCourseRepository((course_section("1"),), (syllabus("1"),))

    with pytest.raises(JudgingError, match="候補の科目がありません"):
        JudgingMaterials(repository).courses(2026, "機")
