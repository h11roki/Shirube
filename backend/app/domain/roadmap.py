from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from app.domain.course import ALL_GRADES, CourseSection, Term
from app.domain.recommendation import Recommendation, RecommendedCourse

NO_CLASS_CODE = ""
SPRING_MONTHS = range(4, 9)


class RoadmapError(ValueError):
    pass


@dataclass(frozen=True)
class Semester:
    grade: int
    term: Term

    def __post_init__(self) -> None:
        if self.grade not in ALL_GRADES:
            raise RoadmapError(
                f"回生は {min(ALL_GRADES)}〜{max(ALL_GRADES)} にしてください: {self.grade}"
            )


ALL_SEMESTERS = tuple(Semester(grade, term) for grade in sorted(ALL_GRADES) for term in Term)


def remaining_semesters(start: Semester) -> tuple[Semester, ...]:
    return ALL_SEMESTERS[ALL_SEMESTERS.index(start) :]


def term_on(day: date) -> Term:
    return Term.SPRING if day.month in SPRING_MONTHS else Term.AUTUMN


def opens_in(section: CourseSection, department: str, year: int, semester: Semester) -> bool:
    return (
        section.offered_to(department, semester.grade, year)
        and (section.term or Term.SPRING) is semester.term
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
    continuing: tuple[PlacedCourse, ...] = ()

    def __post_init__(self) -> None:
        if self.continuing and self.semester.term is not Term.AUTUMN:
            raise RoadmapError(f"{self.semester}: 続きの授業を持てるのは秋学期だけです")
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
        positions = [ALL_SEMESTERS.index(plan.semester) for plan in self.semesters]
        if positions != sorted(set(positions)):
            raise RoadmapError("学期は重ならずに古い順に並べてください")
        names = Counter(placed.course.name for plan in self.semesters for placed in plan.courses)
        repeated = sorted(name for name, count in names.items() if count > 1)
        if repeated:
            raise RoadmapError(f"同じ科目が 2 つの学期にあります: {'、'.join(repeated)}")
        both = sorted(names.keys() & {course.name for course in self.unplaced})
        if both:
            raise RoadmapError(f"置いた科目が置けなかった科目にもあります: {'、'.join(both)}")
        year_long = {
            (plan.semester.grade, placed)
            for plan in self.semesters
            if plan.semester.term is Term.SPRING
            for placed in plan.courses
            if placed.section.term is None
        }
        stray = [
            placed.course.name
            for plan in self.semesters
            for placed in plan.continuing
            if (plan.semester.grade, placed) not in year_long
        ]
        if stray:
            raise RoadmapError(f"春学期に置いていない続きの授業があります: {'、'.join(stray)}")


def _code(section: CourseSection) -> str:
    return section.class_code or NO_CLASS_CODE


def _classes(
    name: str,
    sections: Sequence[CourseSection],
    department: str,
    year: int,
    semesters: Sequence[Semester],
    chosen_classes: Mapping[str, str],
) -> tuple[list[CourseSection], bool]:
    ordered = sorted(sections, key=_code)
    own = [
        section
        for section in ordered
        if department in (section.departments or ())
        and any(opens_in(section, department, year, semester) for semester in semesters)
    ]
    open_together = [
        {_code(section) for section in own if opens_in(section, department, year, semester)}
        for semester in semesters
    ]
    choosable = sorted(set().union(*(codes for codes in open_together if len(codes) >= 2)))
    if not choosable:
        return own or ordered, True
    if name not in chosen_classes:
        return own, False
    if chosen_classes[name] not in choosable:
        listed = "、".join(code or "記号なし" for code in choosable)
        raise RoadmapError(f"{name}: 選べるクラスは {listed} です")
    return [section for section in own if _code(section) == chosen_classes[name]], True


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
    options = {
        name: _classes(name, by_name[name], department, year, semesters, chosen_classes)
        for name in names
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
                    if opens_in(section, department, year, semester)
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
