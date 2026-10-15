import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine

from app.domain.course import Term
from app.domain.syllabus import CourseName
from app.infrastructure.db.courses import SqlCourseRepository
from tests.builders import course_section, syllabus

DATABASE_URL = os.environ.get("DATABASE_URL")
ALEMBIC_INI = Path(__file__).parents[2] / "alembic.ini"
YEAR = 2099

pytestmark = pytest.mark.skipif(DATABASE_URL is None, reason="DATABASE_URL が無い")


@pytest.fixture(scope="module")
def repository() -> Iterator[SqlCourseRepository]:
    assert DATABASE_URL is not None
    command.upgrade(Config(str(ALEMBIC_INI)), "head")
    engine = create_engine(DATABASE_URL)
    repository = SqlCourseRepository(engine)
    yield repository
    repository.replace(YEAR, [], [])
    repository.replace(YEAR + 1, [], [])
    engine.dispose()


def test_sections_and_syllabi_round_trip(repository: SqlCourseRepository) -> None:
    sections = [
        course_section("10001"),
        course_section("10002", term=None, slots=(), departments=None),
    ]
    shared = syllabus("10001", aliases=(CourseName("10002", "別名(6T)"),), year=YEAR)

    repository.replace(YEAR, sections, [shared])

    assert repository.sections(YEAR) == sections
    assert repository.sections(YEAR)[0].term is Term.SPRING
    assert repository.syllabus(YEAR, "10001") == shared
    assert repository.syllabus(YEAR, "10002") == shared
    assert repository.syllabus(YEAR, "99999") is None


def test_replace_swaps_only_the_rows_of_that_year(repository: SqlCourseRepository) -> None:
    repository.replace(YEAR, [course_section("10001")], [syllabus("10001", year=YEAR)])
    repository.replace(YEAR + 1, [course_section("20001")], [])

    repository.replace(YEAR, [course_section("10003")], [])

    assert [section.code for section in repository.sections(YEAR)] == ["10003"]
    assert repository.syllabus(YEAR, "10001") is None
    assert [section.code for section in repository.sections(YEAR + 1)] == ["20001"]
