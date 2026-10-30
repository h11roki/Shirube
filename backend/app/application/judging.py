from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import astuple, dataclass

from app.application.evaluate_selection import Judgment, judgment_of
from app.application.ports import CourseRepository
from app.domain.course import ALL_GRADES, CourseSection
from app.domain.recommendation import Relevance
from app.domain.roadmap import ALL_SEMESTERS, opens_in_any
from app.domain.syllabus import Syllabus

JUDGES = ("engineer", "professor", "student")
REASON_ORDER = ("professor", "student", "engineer")
EVIDENCE_LENGTH = 40
OVERVIEW_LENGTH = 450
OBJECTIVES_LENGTH = 250
SCHEDULE_LENGTH = 350


class JudgingError(ValueError):
    pass


@dataclass(frozen=True)
class Excerpts:
    overview: str
    objectives: str
    schedule: str


def excerpts(page: Syllabus) -> Excerpts:
    themes = "、".join(session.theme for session in page.sessions if session.theme.strip())
    return Excerpts(
        _excerpt(page.overview, OVERVIEW_LENGTH),
        _excerpt(page.objectives, OBJECTIVES_LENGTH),
        _excerpt(themes, SCHEDULE_LENGTH),
    )


@dataclass(frozen=True)
class CourseMaterial:
    name: str
    category: str
    grades: tuple[int, ...]
    page: str
    overview: str
    objectives: str
    schedule: str


@dataclass(frozen=True)
class Vote:
    label: Relevance
    evidence: str

    def __post_init__(self) -> None:
        if not 0 < len(self.evidence) <= EVIDENCE_LENGTH:
            raise JudgingError(f"根拠は 1〜{EVIDENCE_LENGTH} 字にしてください: {self.evidence!r}")


@dataclass(frozen=True)
class JudgedCourse:
    name: str
    page: str
    votes: dict[str, Vote]
    decision: Relevance | None = None

    def __post_init__(self) -> None:
        unknown = sorted(set(self.votes) - set(JUDGES))
        if unknown:
            raise JudgingError(f"{self.name}: 知らない判定者の票があります: {'、'.join(unknown)}")
        if self.decision is not None and len(self.cores) != 1:
            raise JudgingError(f"{self.name}: 決定は中心が 1 票だけの科目にだけ付けます")

    @property
    def cores(self) -> list[str]:
        return [
            judge
            for judge in REASON_ORDER
            if judge in self.votes and self.votes[judge].label is Relevance.CORE
        ]

    @property
    def undecided(self) -> bool:
        return len(self.cores) == 1 and self.decision is None


@dataclass(frozen=True)
class JudgeOutput:
    judge: str
    votes: dict[str, dict[str, Vote]]


def expected_courses(courses: Sequence[JudgedCourse]) -> dict[str, str]:
    ranked = sorted(
        (-len(course.cores), course.name, course.votes[course.cores[0]].evidence)
        for course in courses
        if judgment_of([vote.label for vote in course.votes.values()], course.decision)
        is Judgment.EXPECTED
    )
    return {name: reason for _, name, reason in ranked}


def combine(
    halves: Sequence[Sequence[JudgeOutput]],
    parts: Sequence[Sequence[str]],
    pages: Mapping[str, str],
    occupations: Sequence[str],
) -> dict[str, list[JudgedCourse]]:
    if len(halves) != len(parts):
        raise JudgingError(f"判定者の出力を科目の {len(parts)} つの組に分けて渡してください")
    votes: dict[str, dict[str, dict[str, Vote]]] = {
        occupation: defaultdict(dict) for occupation in occupations
    }
    for index, (outputs, part) in enumerate(zip(halves, parts, strict=True), 1):
        given = sorted(output.judge for output in outputs)
        if given != sorted(JUDGES):
            raise JudgingError(
                f"{index} つ目の組の判定者が 1 体ずつそろっていません: {'、'.join(given)}"
            )
        for output in outputs:
            if output.votes.keys() != set(occupations):
                missing = sorted(set(occupations) - output.votes.keys())
                extra = sorted(output.votes.keys() - set(occupations))
                raise JudgingError(
                    f"{output.judge}: 判定する職業がそろっていません"
                    f"(足りない職業: {'、'.join(missing) or 'なし'}、"
                    f"多い職業: {'、'.join(extra) or 'なし'}。materials から作り直す)"
                )
            for occupation, courses in output.votes.items():
                outside = sorted(set(courses) - set(part))
                if outside:
                    raise JudgingError(
                        f"{output.judge}: {index} つ目の組に無い科目に票があります: "
                        + "、".join(outside)
                    )
                for course, vote in courses.items():
                    votes[occupation][course][output.judge] = vote
    return {
        occupation: [
            JudgedCourse(
                course,
                pages[course],
                {judge: by_judge[judge] for judge in JUDGES if judge in by_judge},
            )
            for course, by_judge in sorted(votes[occupation].items())
        ]
        for occupation in occupations
    }


def decide(
    judged: Mapping[str, Sequence[JudgedCourse]],
    decisions: Mapping[str, Mapping[str, Relevance]],
) -> dict[str, list[JudgedCourse]]:
    decided: dict[str, list[JudgedCourse]] = {}
    for occupation, chosen in decisions.items():
        names = {course.name for course in judged.get(occupation, ()) if course.undecided}
        unknown = sorted(set(chosen) - names)
        if unknown:
            raise JudgingError(
                f"{occupation}: 中心が 1 票だけではない科目に決定があります: {'、'.join(unknown)}"
            )
    for occupation, courses in judged.items():
        chosen = decisions.get(occupation, {})
        decided[occupation] = [
            JudgedCourse(course.name, course.page, course.votes, chosen[course.name])
            if course.name in chosen
            else course
            for course in courses
        ]
    return decided


class JudgingMaterials:
    def __init__(self, courses: CourseRepository) -> None:
        self._courses = courses

    def courses(self, year: int, department: str) -> list[CourseMaterial]:
        page_of = self._courses.syllabus_codes(year)
        by_name: dict[str, list[CourseSection]] = defaultdict(list)
        for section in self._courses.sections(year):
            if section.code in page_of and opens_in_any(section, department, year, ALL_SEMESTERS):
                by_name[section.name].append(section)
        if not by_name:
            raise JudgingError(
                f"{year} 年度の {department} に、シラバスのある候補の科目がありません"
            )
        pages = {
            name: page_of[
                next(
                    (
                        section
                        for section in group
                        if section.departments is not None and department in section.departments
                    ),
                    group[0],
                ).code
            ]
            for name, group in by_name.items()
        }
        syllabi = self._courses.syllabi_of(year, set(pages.values()))
        missing = sorted(name for name, page in pages.items() if page not in syllabi)
        if missing:
            raise JudgingError(f"シラバスが DB にありません: {'、'.join(missing)}")
        return [
            CourseMaterial(
                name,
                "・".join(
                    sorted(
                        {audience.category for section in group for audience in section.audiences}
                    )
                ),
                tuple(
                    grade
                    for grade in sorted(ALL_GRADES)
                    if any(section.offered_to(department, grade, year) for section in group)
                ),
                pages[name],
                *astuple(excerpts(syllabi[pages[name]])),
            )
            for name, group in sorted(by_name.items())
        ]


def _excerpt(text: str, length: int) -> str:
    return " ".join(text.split())[:length]
