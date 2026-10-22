from pathlib import Path

from app.domain.course import Audience, Term, TimeSlot, Weekday
from app.infrastructure.curriculum.ritsumeikan.timetable_pdf import RitsumeikanTimetablePdf

SAMPLE = Path(__file__).parents[1] / "fixtures" / "timetable" / "sample.pdf"


def test_sample_pdf_yields_every_course_row_with_its_term() -> None:
    sections = {section.code: section for section in RitsumeikanTimetablePdf(SAMPLE).sections()}

    assert set(sections) == {"34982", "32453", "34793", "32423", "16806"}
    assert sections["34982"].name == "スポーツ方法実習Ⅰ(A)【バスケットボール】"
    assert sections["32453"].instructors == ("仮名 一郎", "架空 太郎", "仮名 花子")
    assert sections["34793"].audiences == (
        Audience(2020, 2026, frozenset({1, 2, 3, 4}), "立命館"),
        Audience(2016, 2019, frozenset({1, 2, 3, 4}), "教養A"),
    )
    assert sections["32423"].slots == (TimeSlot(Weekday.MON, 4), TimeSlot(Weekday.MON, 5))
    assert sections["32423"].departments == frozenset({"電", "情"})
    assert sections["16806"].term is None
    assert sections["16806"].slots == ()
    assert all(section.term is Term.SPRING for code, section in sections.items() if code != "16806")
