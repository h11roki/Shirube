from collections.abc import Sequence
from uuid import UUID

from app.application.ports import CourseRepository, UserRepository
from app.domain.course import CourseSection, left_out_codes


def left_out_for(
    courses: CourseRepository,
    users: UserRepository,
    owner_id: UUID,
    department: str,
    year: int,
    sections: Sequence[CourseSection],
) -> frozenset[str]:
    return left_out_codes(sections, courses.syllabus_codes(year), department, users.taken(owner_id))
