from dataclasses import dataclass


@dataclass(frozen=True)
class CourseName:
    code: str
    title: str


@dataclass(frozen=True)
class Session:
    label: str
    theme: str
    keywords: str


@dataclass(frozen=True)
class GradingItem:
    kind: str
    percentage: str
    criteria: str


@dataclass(frozen=True)
class Syllabus:
    code: str
    title: str
    aliases: tuple[CourseName, ...]
    year: int
    term_label: str
    slot_label: str
    faculties: tuple[str, ...]
    instructors: tuple[str, ...]
    credits: int
    campus: str
    language: str
    overview: str
    objectives: str
    preparation: str
    schedule_note: str
    sessions: tuple[Session, ...]
    class_format: str
    self_study: str
    grading: tuple[GradingItem, ...]
    grading_note: str
    advice: str
    remarks: str
