from pathlib import Path

from app.infrastructure.scrapers.ritsumeikan.store import RawStore
from app.infrastructure.scrapers.ritsumeikan.stored import StoredSyllabi

FIXTURES = Path(__file__).parents[1] / "fixtures" / "html" / "ritsumeikan"
LISTING = (
    "<table><tbody><tr><th><a href='/syllabus/s/r-syllabus/x/202616806'>"
    "16806:平和人権フィールドスタディ (GR) § 16807:国際平和交流セミナー(GR)</a></th>"
    "<td>理工学部</td><td>通年</td><td></td><td>衣笠</td><td>甲</td><td>日本語</td><td>2</td>"
    "</tr></tbody></table>"
)


def saved_store(tmp_path: Path, with_listing: bool) -> RawStore:
    store = RawStore(tmp_path, 2026)
    store.save_detail("16806", (FIXTURES / "detail_16806.html").read_text(encoding="utf-8"))
    if with_listing:
        store.save_listing("a", [LISTING])
    return store


def test_primary_code_is_read_without_listings(tmp_path: Path) -> None:
    syllabus = StoredSyllabi(saved_store(tmp_path, with_listing=False)).syllabus("16806")

    assert syllabus is not None
    assert syllabus.title == "平和人権フィールドスタディ (GR)"


def test_alias_code_resolves_to_the_primary_page_through_listings(tmp_path: Path) -> None:
    syllabus = StoredSyllabi(saved_store(tmp_path, with_listing=True)).syllabus("16807")

    assert syllabus is not None
    assert syllabus.code == "16806"
    assert [alias.code for alias in syllabus.aliases] == ["16807"]


def test_unknown_or_unsaved_codes_are_none(tmp_path: Path) -> None:
    source = StoredSyllabi(saved_store(tmp_path, with_listing=False))

    assert source.syllabus("16807") is None
    assert source.syllabus("99999") is None
