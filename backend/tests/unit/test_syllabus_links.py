from dataclasses import replace
from uuid import uuid4

from app.application.syllabus_links import SyllabusLinks
from app.domain.plan import Plan
from tests.builders import sample_conditions, sample_plan, syllabus
from tests.fakes import FakeCourseRepository


def test_links_are_the_urls_of_the_courses_in_the_result() -> None:
    courses = FakeCourseRepository(
        syllabi=(
            replace(syllabus("10000"), url="https://syllabus.test/10000"),
            syllabus("10001"),
            replace(syllabus("99999"), url="https://syllabus.test/99999"),
        )
    )

    links = SyllabusLinks(courses).of(sample_plan(uuid4()))

    assert links == {"10000": "https://syllabus.test/10000"}


def test_a_plan_without_a_result_has_no_links() -> None:
    courses = FakeCourseRepository(
        syllabi=(replace(syllabus("10000"), url="https://syllabus.test/10000"),)
    )

    assert SyllabusLinks(courses).of(Plan(uuid4(), uuid4(), sample_conditions())) == {}
