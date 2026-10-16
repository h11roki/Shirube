from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from app.domain.course import ALL_GRADES, CourseSection, Term
from app.domain.recommendation import Recommendation, RecommendedCourse


class RoadmapError(ValueError):
    pass


@dataclass(frozen=True)
class Semester:
    grade: int
    term: Term


def remaining_semesters(grade: int, term: Term) -> tuple[Semester, ...]:
    if grade not in ALL_GRADES:
        raise RoadmapError(f"回生は {min(ALL_GRADES)}〜{max(ALL_GRADES)} にしてください: {grade}")
    order = list(Term)
    return tuple(
        Semester(semester_grade, semester_term)
        for semester_grade in sorted(ALL_GRADES)
        for semester_term in order
        if (semester_grade, order.index(semester_term)) >= (grade, order.index(term))
    )


@dataclass(frozen=True)
class PlacedCourse:
    course: RecommendedCourse
    section: CourseSection
    class_confirmed: bool


@dataclass(frozen=True)
class SemesterPlan:
    semester: Semester
    courses: tuple[PlacedCourse, ...]

    def __post_init__(self) -> None:
        slots = Counter(slot for placed in self.courses for slot in placed.section.slots)
        if any(count > 1 for count in slots.values()):
            raise RoadmapError(f"{self.semester}: 同じコマに 2 つの授業があります")

    @property
    def credits(self) -> int:
        return sum(placed.section.credits for placed in self.courses)


@dataclass(frozen=True)
class Roadmap:
    semesters: tuple[SemesterPlan, ...]
    unplaced: tuple[RecommendedCourse, ...]

    def __post_init__(self) -> None:
        names = Counter(placed.course.name for plan in self.semesters for placed in plan.courses)
        repeated = sorted(name for name, count in names.items() if count > 1)
        if repeated:
            raise RoadmapError(f"同じ科目が 2 つの学期にあります: {'、'.join(repeated)}")


def _classes(
    name: str,
    sections: Sequence[CourseSection],
    department: str,
    chosen_classes: Mapping[str, str],
) -> tuple[list[CourseSection], bool]:
    own = [section for section in sections if department in (section.departments or ())]
    ordered = sorted(sections, key=lambda section: section.class_code or "")
    if len(own) < 2:
        if name in chosen_classes:
            raise RoadmapError(f"{name}: 学科で分かれたクラスではないので、クラスを選べません")
        return ordered, True
    if name not in chosen_classes:
        return ordered, False
    chosen = [section for section in ordered if section.class_code == chosen_classes[name]]
    if not chosen:
        raise RoadmapError(f"{name}: クラス {chosen_classes[name]} はありません")
    return chosen, True


def place(
    recommendation: Recommendation,
    sections: Sequence[CourseSection],
    department: str,
    year: int,
    semesters: Sequence[Semester],
    credit_limit: int,
    chosen_classes: Mapping[str, str],
) -> Roadmap:
    if credit_limit <= 0:
        raise RoadmapError(f"単位の上限は 1 以上にしてください: {credit_limit}")
    names = {course.name for course in recommendation.courses}
    unknown = sorted(chosen_classes.keys() - names)
    if unknown:
        raise RoadmapError(f"推薦に無い科目のクラスが選ばれています: {'、'.join(unknown)}")
    by_name: dict[str, list[CourseSection]] = {name: [] for name in names}
    for section in sections:
        if section.name in by_name:
            by_name[section.name].append(section)
    options = {name: _classes(name, by_name[name], department, chosen_classes) for name in names}
    placed: set[str] = set()
    plans = []
    for semester in semesters:
        courses: list[PlacedCourse] = []
        for course in recommendation.courses:
            if course.name in placed:
                continue
            classes, confirmed = options[course.name]
            credits = sum(placed_course.section.credits for placed_course in courses)
            occupied = {slot for placed_course in courses for slot in placed_course.section.slots}
            fitting = next(
                (
                    section
                    for section in classes
                    if section.offered_to(department, semester.grade, year)
                    and (section.term or Term.SPRING) is semester.term
                    and credits + section.credits <= credit_limit
                    and occupied.isdisjoint(section.slots)
                ),
                None,
            )
            if fitting is not None:
                courses.append(PlacedCourse(course, fitting, confirmed))
                placed.add(course.name)
        plans.append(SemesterPlan(semester, tuple(courses)))
    unplaced = tuple(course for course in recommendation.courses if course.name not in placed)
    return Roadmap(tuple(plans), unplaced)
