from dataclasses import replace

from app.domain.course import Audience, CourseSection
from tests.builders import course_section


def with_audiences(*audiences: Audience) -> CourseSection:
    return replace(
        course_section("10001", departments=frozenset({"電", "情"})), audiences=audiences
    )


def test_course_is_offered_to_the_grade_whose_cohort_it_lists_this_year() -> None:
    upper_years = with_audiences(Audience(2020, 2024, frozenset({3, 4}), "専門"))

    assert upper_years.offered_to("情", 3, 2026)
    assert upper_years.offered_to("情", 4, 2026)
    assert not upper_years.offered_to("情", 1, 2026)
    assert not upper_years.offered_to("情", 2, 2026)


def test_grade_must_be_eligible_even_when_the_cohort_is_listed() -> None:
    second_year_on = with_audiences(Audience(2016, 2026, frozenset({2, 3, 4}), "専門"))

    assert not second_year_on.offered_to("情", 1, 2026)
    assert second_year_on.offered_to("情", 2, 2026)


def test_class_only_for_old_curriculum_cohorts_is_not_offered_to_current_grades() -> None:
    old_curriculum = with_audiences(Audience(2016, 2019, frozenset({1, 2, 3, 4}), "基礎専"))

    assert not any(old_curriculum.offered_to("情", grade, 2026) for grade in range(1, 5))


def test_department_must_match_unless_the_course_is_for_every_department() -> None:
    first_year = Audience(2020, 2026, frozenset({1, 2, 3, 4}), "専門")

    assert not with_audiences(first_year).offered_to("機", 1, 2026)
    assert replace(with_audiences(first_year), departments=None).offered_to("機", 1, 2026)
