from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, func, select

from app.domain.syllabus import CourseName
from app.infrastructure.db.courses import SqlCourseRepository
from app.infrastructure.db.models import CourseSectionRow
from tests.builders import course_section, syllabus

YEAR = 2099


@pytest.fixture
def repository(engine: Engine) -> Iterator[SqlCourseRepository]:
    repository = SqlCourseRepository(engine)
    yield repository
    for year in (YEAR, YEAR + 1):
        repository.replace_sections(year, [])
        repository.replace_syllabi(year, [])


def test_sections_and_syllabi_round_trip(repository: SqlCourseRepository) -> None:
    sections = [
        course_section("10001"),
        course_section("10002", term=None, slots=(), departments=None),
    ]
    shared = syllabus("10001", aliases=(CourseName("10002", "別名(6T)"),), year=YEAR)

    repository.replace_sections(YEAR, sections)
    repository.replace_syllabi(YEAR, [shared])

    assert repository.sections(YEAR) == sections
    assert repository.syllabus(YEAR, "10001") == shared
    assert repository.syllabus(YEAR, "10002") == shared
    assert repository.syllabus(YEAR, "99999") is None


def test_all_syllabi_of_a_year_come_back_with_their_aliases(
    repository: SqlCourseRepository,
) -> None:
    aliases = (CourseName("10002", "乙"), CourseName("10003", "丙"))
    pages = [syllabus("10001", aliases=aliases, year=YEAR), syllabus("20001", year=YEAR)]
    repository.replace_syllabi(YEAR, list(reversed(pages)))
    repository.replace_syllabi(YEAR + 1, [syllabus("30001", year=YEAR + 1)])

    assert repository.syllabi(YEAR) == pages


def test_all_departments_are_stored_as_sql_null(
    engine: Engine, repository: SqlCourseRepository
) -> None:
    repository.replace_sections(YEAR, [course_section("10002", departments=None)])

    with engine.connect() as connection:
        nulls = connection.scalar(
            select(func.count())
            .select_from(CourseSectionRow)
            .where(CourseSectionRow.year == YEAR, CourseSectionRow.departments.is_(None))
        )
    assert nulls == 1


def test_each_source_is_replaced_without_touching_the_other(
    repository: SqlCourseRepository,
) -> None:
    repository.replace_sections(YEAR, [course_section("10001")])
    repository.replace_syllabi(YEAR, [syllabus("10001", year=YEAR)])

    repository.replace_syllabi(YEAR, [syllabus("10003", year=YEAR)])
    repository.replace_sections(YEAR, [course_section("10002")])

    assert [section.code for section in repository.sections(YEAR)] == ["10002"]
    assert repository.syllabus(YEAR, "10001") is None
    assert repository.syllabus(YEAR, "10003") == syllabus("10003", year=YEAR)


def test_replacing_a_year_keeps_the_other_years(repository: SqlCourseRepository) -> None:
    repository.replace_sections(YEAR + 1, [course_section("20001")])
    repository.replace_syllabi(YEAR + 1, [syllabus("20001", year=YEAR + 1)])

    repository.replace_sections(YEAR, [course_section("10001")])
    repository.replace_syllabi(YEAR, [syllabus("10001", year=YEAR)])

    assert [section.code for section in repository.sections(YEAR + 1)] == ["20001"]
    assert repository.syllabus(YEAR + 1, "20001") == syllabus("20001", year=YEAR + 1)
