from uuid import UUID

from app.presentation.cli.plan import render
from tests.builders import sample_plan

PLAN_ID = UUID("8888666a-9ab0-48db-ba61-cf526a15dc0d")


def test_render_lists_each_semester_with_slots_classes_and_reasons() -> None:
    assert render(sample_plan(PLAN_ID)) == (
        f"Plan {PLAN_ID}\n"
        "職業: 職業 → 解釈した職業\n"
        "前提: 前提の文\n"
        "スキル: 甲 / 乙 / 丙\n"
        "条件: 情、2026 年度の時間割、3 回生 春学期から、1 学期 16 単位まで\n"
        "3 回生 春学期 6 単位\n"
        "  中心 科目A(月1・月2、6T): 理由A\n"
        "  中心 科目B(水3、6T): 理由B\n"
        "  土台 科目C(→ 科目A)(コマなし、6A、クラス未確定): 理由C\n"
        "3 回生 秋学期 0 単位\n"
        "  続き 科目B(水3、6T): 理由B\n"
        "4 回生 春学期 0 単位\n"
        "4 回生 秋学期 0 単位\n"
        "置けなかった科目: 科目D\n"
        "中心につながらず外した土台: 科目E(→ 科目F)"
    )
