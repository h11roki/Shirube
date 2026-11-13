from dataclasses import replace
from uuid import uuid4

from app.application.syllabus_links import PlanLinks, SyllabusLinks
from app.domain.plan import Plan
from tests.builders import (
    moved_to_class,
    sample_conditions,
    sample_plan,
    sample_plan_with_fixed,
    syllabus,
)
from tests.fakes import FakeCourseRepository


def test_links_are_the_urls_of_the_courses_in_the_result() -> None:
    courses = FakeCourseRepository(
        syllabi=(
            replace(syllabus("10000"), url="https://syllabus.test/10000"),
            syllabus("10001"),
            replace(syllabus("10002", year=2025), url="https://syllabus.test/2025/10002"),
            replace(syllabus("99999"), url="https://syllabus.test/99999"),
        )
    )

    links = SyllabusLinks(courses).of(sample_plan(uuid4()))

    assert links.urls == {"10000": "https://syllabus.test/10000"}


def test_the_pages_of_the_fixed_courses_are_linked_too() -> None:
    courses = FakeCourseRepository(
        syllabi=(
            replace(syllabus("10000"), url="https://syllabus.test/10000"),
            replace(syllabus("10010"), url="https://syllabus.test/10010"),
        )
    )

    links = SyllabusLinks(courses).of(sample_plan_with_fixed(uuid4()))

    assert links.urls == {
        "10000": "https://syllabus.test/10000",
        "10010": "https://syllabus.test/10010",
    }


def test_a_plan_without_a_result_has_no_links() -> None:
    courses = FakeCourseRepository(
        syllabi=(replace(syllabus("10000"), url="https://syllabus.test/10000"),)
    )

    assert SyllabusLinks(courses).of(Plan(uuid4(), uuid4(), sample_conditions())) == PlanLinks()


def test_a_placed_course_links_to_the_page_of_the_class_it_is_placed_in() -> None:
    courses = FakeCourseRepository(
        syllabi=(
            replace(syllabus("10000"), url="https://syllabus.test/10000"),
            replace(syllabus("10005"), url="https://syllabus.test/10005"),
        )
    )

    links = SyllabusLinks(courses).of(moved_to_class(sample_plan(uuid4()), "10005", "6B"))

    assert links.page_of("10005", "10000") == "10005"
    assert links.urls["10005"] == "https://syllabus.test/10005"


def test_a_class_without_its_own_page_keeps_the_page_of_the_course() -> None:
    courses = FakeCourseRepository(
        syllabi=(replace(syllabus("10000"), url="https://syllabus.test/10000"),)
    )

    links = SyllabusLinks(courses).of(moved_to_class(sample_plan(uuid4()), "10099", "6B"))

    assert links.page_of("10099", "10000") == "10000"
    assert links.urls["10000"] == "https://syllabus.test/10000"
