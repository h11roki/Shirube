from app.domain.course import Audience, Term, TimeSlot, Weekday
from app.infrastructure.curriculum.ritsumeikan.timetable_pdf import normalize_row, section_from_row

ROW = [
    "月",
    "1-2",
    "専門",
    "電",
    "24-20",
    "3",
    "32453",
    "電動移動機械システム",
    "B8",
    "2",
    "川畑 良尚、峯元 高\n志、福水 洋平",
    "Ｃ３０５",
    "本",
]


def row(**overrides: str) -> list[str]:
    columns = [
        "weekday",
        "period",
        "category",
        "departments",
        "entry_years",
        "grades",
        "code",
        "name",
        "class_code",
        "credits",
        "instructors",
        "room",
        "registration",
    ]
    values = dict(zip(columns, ROW, strict=True)) | overrides
    return [values[column] for column in columns]


def test_row_becomes_a_section_with_one_slot() -> None:
    section = section_from_row(Term.SPRING, ROW)

    assert section.code == "32453"
    assert section.name == "電動移動機械システム"
    assert section.class_code == "B8"
    assert section.term is Term.SPRING
    assert section.slots == (TimeSlot(Weekday.MON, 1),)
    assert section.departments == frozenset({"電"})
    assert section.audiences == (Audience(2020, 2024, frozenset({3, 4}), "専門"),)
    assert section.credits == 2
    assert section.instructors == ("川畑 良尚", "峯元 高志", "福水 洋平")
    assert section.room == "Ｃ３０５"
    assert section.registration == "本"
    assert section.note is None


def test_period_span_covers_consecutive_periods() -> None:
    section = section_from_row(Term.SPRING, row(period="7-10"))

    assert section.slots == (TimeSlot(Weekday.MON, 4), TimeSlot(Weekday.MON, 5))


def test_on_demand_row_has_no_slot_and_no_term() -> None:
    section = section_from_row(None, row(weekday="@", period="@", room="-"))

    assert section.slots == ()
    assert section.term is None
    assert section.room is None


def test_all_departments_is_represented_by_none() -> None:
    assert section_from_row(Term.SPRING, row(departments="全")).departments is None


def test_wrapped_department_list_is_split() -> None:
    section = section_from_row(Term.AUTUMN, row(departments="数・物・情・\n機"))

    assert section.departments == frozenset({"数", "物", "情", "機"})


def test_variants_separated_by_slash_become_separate_audiences() -> None:
    section = section_from_row(
        Term.SPRING, row(category="立命館/教養A", entry_years="26-20/19-16", grades="1")
    )

    assert section.audiences == (
        Audience(2020, 2026, frozenset({1, 2, 3, 4}), "立命館"),
        Audience(2016, 2019, frozenset({1, 2, 3, 4}), "教養A"),
    )


def test_only_marker_restricts_grades_to_the_listed_ones() -> None:
    section = section_from_row(Term.AUTUMN, row(grades="1.2のみ"))

    assert section.audiences[0].eligible_grades == frozenset({1, 2})


def test_grade_range_with_only_marker_expands_to_each_grade() -> None:
    section = section_from_row(Term.AUTUMN, row(grades="1～4のみ"))

    assert section.audiences[0].eligible_grades == frozenset({1, 2, 3, 4})


def test_single_entry_year_is_a_range_of_one() -> None:
    section = section_from_row(Term.SPRING, row(entry_years="26"))

    assert section.audiences[0].entry_year_from == 2026
    assert section.audiences[0].entry_year_to == 2026


def test_note_after_marker_is_split_from_name() -> None:
    section = section_from_row(Term.SPRING, row(name="論理回路 ※2020年度以前入学者のみ受講可"))

    assert section.name == "論理回路"
    assert section.note == "2020年度以前入学者のみ受講可"


def test_wrapped_name_is_joined() -> None:
    section = section_from_row(Term.SPRING, row(name="スポーツ方法実習Ⅰ(A)【バスケットボー\nル】"))

    assert section.name == "スポーツ方法実習Ⅰ(A)【バスケットボール】"


def test_carried_over_row_marks_are_removed() -> None:
    carried = ["I火", "I @", "I教 養B", "I全", "I 19-16", "I 1", "I310 61", "Basic Skills"]
    carried += ["IG2", "I2", "庄子 萌、羽谷 沙織、\nI石川 涼子", "I -", "I抽 選"]

    section = section_from_row(Term.AUTUMN, normalize_row(carried))

    assert section.code == "31061"
    assert section.slots == ()
    assert section.audiences == (Audience(2016, 2019, frozenset({1, 2, 3, 4}), "教養B"),)
    assert section.instructors == ("庄子 萌", "羽谷 沙織", "石川 涼子")
    assert section.registration == "抽選"
