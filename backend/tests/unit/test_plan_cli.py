from uuid import UUID

from app.domain.plan import Plan, PlanStatus
from app.presentation.cli.plan import render
from tests.builders import SAMPLE_OWNER, sample_conditions, sample_plan, sample_plan_with_taken

PLAN_ID = UUID("8888666a-9ab0-48db-ba61-cf526a15dc0d")


def test_render_lists_each_semester_with_slots_classes_and_reasons() -> None:
    assert render(sample_plan(PLAN_ID)) == (
        f"Plan {PLAN_ID}\n"
        "状態: 完了\n"
        "職業: 職業 → 解釈した職業\n"
        "前提: 前提の文\n"
        "スキル: 甲 / 乙 / 丙\n"
        "条件: 情、2026 年度の時間割、3 回生 春学期から、1 学期 16 単位まで\n"
        "クラスの選択: 科目Z=6B\n"
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


def test_render_lists_the_courses_left_out_as_taken() -> None:
    lines = render(sample_plan_with_taken(PLAN_ID)).splitlines()

    assert "もう取った科目: 科目D" in lines
    assert not any(line.startswith("置けなかった科目") for line in lines)


def test_render_shows_the_conditions_of_a_plan_without_a_result() -> None:
    waiting = Plan(PLAN_ID, SAMPLE_OWNER, sample_conditions())
    failed = Plan(PLAN_ID, SAMPLE_OWNER, sample_conditions(), PlanStatus.FAILED, failure="失敗の文")
    conditions = (
        "職業: 職業\n"
        "条件: 情、2026 年度の時間割、3 回生 春学期から、1 学期 16 単位まで\n"
        "クラスの選択: 科目Z=6B"
    )

    assert render(waiting) == f"Plan {PLAN_ID}\n状態: 待ち\n{conditions}"
    assert render(failed) == f"Plan {PLAN_ID}\n状態: 失敗(失敗の文)\n{conditions}"
