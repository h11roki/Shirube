from collections.abc import Mapping, Set
from dataclasses import dataclass

from app.domain.chunk import ChunkSection


@dataclass(frozen=True)
class ChunkHit:
    syllabus_code: str
    section: ChunkSection
    similarity: float


@dataclass(frozen=True)
class CourseMatch:
    name: str
    similarity: float
    syllabus_code: str
    section: ChunkSection


def rank_courses(
    hits: list[ChunkHit], names_of_page: Mapping[str, Set[str]], limit: int
) -> list[CourseMatch]:
    best: dict[str, CourseMatch] = {}
    for hit in hits:
        for name in names_of_page.get(hit.syllabus_code, ()):
            current = best.get(name)
            if current is None or hit.similarity > current.similarity:
                best[name] = CourseMatch(name, hit.similarity, hit.syllabus_code, hit.section)
    ranked = sorted(best.values(), key=lambda match: (-match.similarity, match.name))
    return ranked[:limit]
