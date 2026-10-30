from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence, Set
from dataclasses import dataclass

from app.domain.course import ALL_GRADES, CourseSection, Term
from app.domain.recommendation import Recommendation, RecommendedCourse

NO_CLASS_CODE = ""
TERM_NAMES = {Term.SPRING: "春学期", Term.AUTUMN: "秋学期"}
DEFAULT_START_TERM = Term.SPRING


class RoadmapError(ValueError):
    pass


class ClassChoiceError(RoadmapError):
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

    def __str__(self) -> str:
        return f"{self.grade} 回生 {TERM_NAMES[self.term]}"


ALL_SEMESTERS = tuple(Semester(grade, term) for grade in sorted(ALL_GRADES) for term in Term)


def remaining_semesters(start: Semester) -> tuple[Semester, ...]:
    return ALL_SEMESTERS[ALL_SEMESTERS.index(start) :]


def opens_in(section: CourseSection, department: str, year: int, semester: Semester) -> bool:
    return (
        section.offered_to(department, semester.grade, year)
        and (section.term or Term.SPRING) is semester.term
    )


def opens_in_any(
    section: CourseSection, department: str, year: int, semesters: Sequence[Semester]
) -> bool:
    return any(opens_in(section, department, year, semester) for semester in semesters)


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
    taken: tuple[RecommendedCourse, ...] = ()
    offered_earlier: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        positions = [ALL_SEMESTERS.index(plan.semester) for plan in self.semesters]
        if positions != sorted(set(positions)):
            raise RoadmapError("学期は重ならずに古い順に並べてください")
        names = Counter(placed.course.name for plan in self.semesters for placed in plan.courses)
        repeated = sorted(name for name, count in names.items() if count > 1)
        if repeated:
            raise RoadmapError(f"同じ科目が 2 つの学期にあります: {'、'.join(repeated)}")
        unplaced = {course.name for course in self.unplaced}
        both = sorted(names.keys() & unplaced)
        if both:
            raise RoadmapError(f"置いた科目が置けなかった科目にもあります: {'、'.join(both)}")
        taken = {course.name for course in self.taken}
        kept = sorted(taken & (names.keys() | unplaced))
        if kept:
            raise RoadmapError(f"もう取った科目が道標にも残っています: {'、'.join(kept)}")
        unasked = sorted(taken - self.offered_earlier)
        if unasked:
            raise RoadmapError(
                f"前の学期に開講されていない科目を取ったことにしています: {'、'.join(unasked)}"
            )
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


def _split_classes(
    sections: Sequence[CourseSection],
    department: str,
    year: int,
    semesters: Sequence[Semester],
) -> tuple[list[CourseSection], list[str]]:
    own = [
        section
        for section in sorted(sections, key=_code)
        if department in (section.departments or ())
        and opens_in_any(section, department, year, semesters)
    ]
    open_together = [
        {_code(section) for section in own if opens_in(section, department, year, semester)}
        for semester in semesters
    ]
    choosable = sorted(set().union(*(codes for codes in open_together if len(codes) >= 2)))
    return own, choosable


def _require_choosable(name: str, chosen: str, choosable: Sequence[str]) -> None:
    if chosen not in choosable:
        listed = "、".join(code or "記号なし" for code in choosable)
        raise ClassChoiceError(f"{name}: 選べるクラスは {listed} です")


def require_class_choices(
    sections: Sequence[CourseSection],
    department: str,
    year: int,
    semesters: Sequence[Semester],
    chosen_classes: Mapping[str, str],
) -> None:
    if not chosen_classes:
        return
    choosable = {
        choice.name: choice.class_codes
        for choice in class_choices(sections, department, year, semesters)
    }
    for name, chosen in chosen_classes.items():
        if name in choosable:
            _require_choosable(name, chosen, choosable[name])


@dataclass(frozen=True)
class ClassChoice:
    name: str
    class_codes: tuple[str, ...]


def class_choices(
    sections: Sequence[CourseSection],
    department: str,
    year: int,
    semesters: Sequence[Semester],
) -> list[ClassChoice]:
    by_name: dict[str, list[CourseSection]] = defaultdict(list)
    for section in sections:
        by_name[section.name].append(section)
    choices = []
    for name in sorted(by_name):
        _, choosable = _split_classes(by_name[name], department, year, semesters)
        if choosable:
            choices.append(ClassChoice(name, tuple(choosable)))
    return choices


def _classes(
    name: str,
    sections: Sequence[CourseSection],
    department: str,
    year: int,
    semesters: Sequence[Semester],
    chosen_classes: Mapping[str, str],
) -> tuple[list[CourseSection], bool]:
    own, choosable = _split_classes(sections, department, year, semesters)
    if not choosable:
        return own or sorted(sections, key=_code), True
    if name not in chosen_classes:
        return own, False
    _require_choosable(name, chosen_classes[name], choosable)
    return [section for section in own if _code(section) == chosen_classes[name]], True


def place(
    recommendation: Recommendation,
    sections: Sequence[CourseSection],
    department: str,
    year: int,
    semesters: Sequence[Semester],
    credit_limit: int,
    chosen_classes: Mapping[str, str],
    taken: Set[str] = frozenset(),
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
    earlier = ALL_SEMESTERS[: ALL_SEMESTERS.index(semesters[0])] if semesters else ()
    offered_earlier = frozenset(
        name
        for name in names
        if any(
            opens_in(section, department, year, semester)
            for section in by_name[name]
            for semester in earlier
        )
    )
    skipped = offered_earlier & taken
    year_long: dict[int, list[PlacedCourse]] = defaultdict(list)
    placed: set[str] = set()
    plans = []
    for semester in semesters:
        continuing = tuple(year_long[semester.grade]) if semester.term is Term.AUTUMN else ()
        courses: list[PlacedCourse] = []
        credits = 0
        occupied = {slot for carried in continuing for slot in carried.section.slots}
        for course in recommendation.courses:
            if course.name in placed or course.name in skipped:
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
            if fitting.term is None and fitting.slots:
                year_long[semester.grade].append(placed_course)
        plans.append(SemesterPlan(semester, tuple(courses), continuing))
    unplaced = tuple(
        course
        for course in recommendation.courses
        if course.name not in placed and course.name not in skipped
    )
    left_out = tuple(course for course in recommendation.courses if course.name in skipped)
    return Roadmap(tuple(plans), unplaced, left_out, offered_earlier)
