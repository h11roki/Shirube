from collections import Counter, defaultdict
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


ALL_SEMESTERS = tuple(Semester(grade, term) for grade in sorted(ALL_GRADES) for term in Term)


def remaining_semesters(grade: int, term: Term) -> tuple[Semester, ...]:
    if grade not in ALL_GRADES:
        raise RoadmapError(f"回生は {min(ALL_GRADES)}〜{max(ALL_GRADES)} にしてください: {grade}")
    return ALL_SEMESTERS[ALL_SEMESTERS.index(Semester(grade, term)) :]


@dataclass(frozen=True)
class PlacedCourse:
    course: RecommendedCourse
    section: CourseSection
    class_confirmed: bool


@dataclass(frozen=True)
class SemesterPlan:
    semester: Semester
    courses: tuple[PlacedCourse, ...]
    continuing: tuple[PlacedCourse, ...] = ()

    def __post_init__(self) -> None:
        slots = Counter(
            slot for placed in self.courses + self.continuing for slot in placed.section.slots
        )
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
        if any(plan.semester not in ALL_SEMESTERS for plan in self.semesters):
            raise RoadmapError("回生は 1〜4、学期は春か秋にしてください")
        positions = [ALL_SEMESTERS.index(plan.semester) for plan in self.semesters]
        if positions != sorted(set(positions)):
            raise RoadmapError("学期は重ならずに古い順に並べてください")
        names = Counter(placed.course.name for plan in self.semesters for placed in plan.courses)
        repeated = sorted(name for name, count in names.items() if count > 1)
        if repeated:
            raise RoadmapError(f"同じ科目が 2 つの学期にあります: {'、'.join(repeated)}")


def _classes(
    name: str,
    sections: Sequence[CourseSection],
    department: str,
    year: int,
    semesters: Sequence[Semester],
    chosen_classes: Mapping[str, str],
) -> tuple[list[CourseSection], bool]:
    ordered = sorted(sections, key=lambda section: section.class_code or "")
    own = [
        section
        for section in ordered
        if department in (section.departments or ())
        and any(section.offered_to(department, semester.grade, year) for semester in semesters)
    ]
    codes = sorted({section.class_code or "" for section in own})
    if len(codes) < 2:
        if name in chosen_classes:
            raise RoadmapError(f"{name}: 学科で分かれたクラスではないので、クラスを選べません")
        return ordered, True
    if name not in chosen_classes:
        return own, False
    chosen = [section for section in own if section.class_code == chosen_classes[name]]
    if not chosen:
        raise RoadmapError(f"{name}: 選べるクラスは {'、'.join(codes)} です")
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
    by_name: dict[str, list[CourseSection]] = {name: [] for name in names}
    for section in sections:
        if section.name in by_name:
            by_name[section.name].append(section)
    chosen = {name: code for name, code in chosen_classes.items() if name in names}
    options = {
        name: _classes(name, by_name[name], department, year, semesters, chosen) for name in names
    }
    year_long: dict[int, list[PlacedCourse]] = defaultdict(list)
    placed: set[str] = set()
    plans = []
    for semester in semesters:
        continuing = tuple(year_long[semester.grade]) if semester.term is Term.AUTUMN else ()
        courses: list[PlacedCourse] = []
        credits = 0
        occupied = {slot for carried in continuing for slot in carried.section.slots}
        for course in recommendation.courses:
            if course.name in placed:
                continue
            classes, confirmed = options[course.name]
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
            if fitting is None:
                continue
            placed_course = PlacedCourse(course, fitting, confirmed)
            courses.append(placed_course)
            placed.add(course.name)
            credits += fitting.credits
            occupied.update(fitting.slots)
            if fitting.term is None:
                year_long[semester.grade].append(placed_course)
        plans.append(SemesterPlan(semester, tuple(courses), continuing))
    unplaced = tuple(course for course in recommendation.courses if course.name not in placed)
    return Roadmap(tuple(plans), unplaced)
