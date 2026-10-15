from dataclasses import replace

from app.domain.chunk import ChunkSection, SyllabusChunk, chunks_of
from app.domain.syllabus import Session
from tests.builders import syllabus


def test_overview_objectives_and_schedule_become_chunks_headed_by_the_title() -> None:
    chunks = chunks_of(syllabus("10001"))

    assert [chunk.section for chunk in chunks] == [
        ChunkSection.OVERVIEW,
        ChunkSection.OBJECTIVES,
        ChunkSection.SCHEDULE,
    ]
    assert chunks[0] == SyllabusChunk(
        "10001", ChunkSection.OVERVIEW, "科目10001(6T)\n授業の概要と方法\n概要\n\n段落"
    )
    assert chunks[1].text == "科目10001(6T)\n受講生の到達目標\n目標"


def test_schedule_lists_themes_and_keywords_without_session_labels() -> None:
    page = replace(
        syllabus("10001"),
        sessions=(Session("第1回", "導入", "語"), Session("2-3", "展開", ""), Session("-", "", "")),
    )

    schedule = chunks_of(page)[-1]

    assert schedule.text == "科目10001(6T)\n授業スケジュール\n導入\n語\n展開"


def test_empty_sections_are_left_out() -> None:
    page = replace(syllabus("10001"), objectives="  ", sessions=())

    assert [chunk.section for chunk in chunks_of(page)] == [ChunkSection.OVERVIEW]


def test_content_hash_follows_the_text_only() -> None:
    first = SyllabusChunk("10001", ChunkSection.OVERVIEW, "本文")
    same_text = SyllabusChunk("20002", ChunkSection.SCHEDULE, "本文")
    other_text = SyllabusChunk("10001", ChunkSection.OVERVIEW, "本文。")

    assert first.content_hash == same_text.content_hash
    assert first.content_hash != other_text.content_hash
    assert len(first.content_hash) == 64
