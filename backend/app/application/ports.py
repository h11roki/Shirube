from typing import Protocol

from app.domain.course import CourseSection


class TimetableSource(Protocol):
    def sections(self) -> list[CourseSection]: ...
