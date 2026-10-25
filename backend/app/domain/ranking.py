from collections import deque
from collections.abc import Mapping, Sequence, Set
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


def take_turns(rankings: Sequence[Sequence[CourseMatch]], limit: int) -> list[CourseMatch]:
    queues = deque(iter(ranked) for ranked in rankings)
    taken: dict[str, CourseMatch] = {}
    while queues and len(taken) < limit:
        queue = queues.popleft()
        match = next((match for match in queue if match.name not in taken), None)
        if match is not None:
            taken[match.name] = match
            queues.append(queue)
    return list(taken.values())
