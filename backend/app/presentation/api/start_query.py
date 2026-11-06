from dataclasses import dataclass
from typing import Annotated

from fastapi import Query

from app.domain.course import ALL_GRADES, Term
from app.domain.roadmap import DEFAULT_START_TERM, Semester
from app.presentation.schemas.plans import DepartmentName


@dataclass(frozen=True)
class StartQuery:
    department: str
    start: Semester


def start_query(
    department: Annotated[DepartmentName, Query()],
    grade: Annotated[int, Query(ge=min(ALL_GRADES), le=max(ALL_GRADES))],
    term: Term = DEFAULT_START_TERM,
) -> StartQuery:
    return StartQuery(department, Semester(grade, term))
