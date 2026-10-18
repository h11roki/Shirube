import argparse
import sys
from uuid import UUID

from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.application.ports import PlanFormatError
from app.application.search_courses import SearchError
from app.domain.course import ALL_GRADES, Term, Weekday
from app.domain.plan import Plan, PlanError, PlanStatus
from app.domain.roadmap import PlacedCourse, RoadmapError, Semester, term_on
from app.infrastructure.db.plans import SqlPlanRepository
from app.infrastructure.db.users import SqlUserRepository
from app.presentation.cli.labels import (
    RELEVANCE_LABELS,
    profile_lines,
    unlinked_lines,
    with_prerequisite,
)
from app.presentation.cli.options import add_department_option, add_year_option
from app.presentation.composition import (
    build_plans,
    database_engine,
    load_settings,
    request_plan,
    university_today,
)

CLI_SUBJECT = "cli:local"
WEEKDAY_LABELS = {
    Weekday.MON: "月",
    Weekday.TUE: "火",
    Weekday.WED: "水",
    Weekday.THU: "木",
    Weekday.FRI: "金",
    Weekday.SAT: "土",
    Weekday.SUN: "日",
}
STATUS_LABELS = {
    PlanStatus.PENDING: "待ち",
    PlanStatus.RUNNING: "作成中",
    PlanStatus.SUCCEEDED: "完了",
    PlanStatus.FAILED: "失敗",
}


def _placed(label: str, placed: PlacedCourse) -> str:
    course = placed.course
    section = placed.section
    where = [
        "・".join(f"{WEEKDAY_LABELS[slot.weekday]}{slot.period}" for slot in section.slots)
        or "コマなし",
        *([section.class_code] if section.class_code else []),
        *([] if placed.class_confirmed else ["クラス未確定"]),
    ]
    name = with_prerequisite(course.name, course.prerequisite_for)
    return f"  {label} {name}({'、'.join(where)}): {course.reason}"


def render(plan: Plan) -> str:
    conditions = plan.conditions
    result = plan.result
    chosen = "、".join(f"{name}={code}" for name, code in conditions.chosen_classes)
    lines = [
        f"Plan {plan.id}",
        f"状態: {STATUS_LABELS[plan.status]}" + (f"({plan.failure})" if plan.failure else ""),
        *(
            [f"職業: {conditions.occupation}"]
            if result is None
            else profile_lines(result.recommendation.profile)
        ),
        f"条件: {conditions.department}、{conditions.year} 年度の時間割、"
        f"{conditions.start}から、1 学期 {conditions.credit_limit} 単位まで",
        *([f"クラスの選択: {chosen}"] if chosen else []),
    ]
    if result is None:
        return "\n".join(lines)
    for semester_plan in result.roadmap.semesters:
        lines.append(f"{semester_plan.semester} {semester_plan.credits} 単位")
        lines += [
            _placed(RELEVANCE_LABELS[placed.course.relevance], placed)
            for placed in semester_plan.courses
        ]
        lines += [_placed("続き", placed) for placed in semester_plan.continuing]
    if result.roadmap.unplaced:
        names = "、".join(course.name for course in result.roadmap.unplaced)
        lines.append(f"置けなかった科目: {names}")
    lines += unlinked_lines(result.recommendation.unlinked)
    return "\n".join(lines)


def _chosen_class(text: str) -> tuple[str, str]:
    name, separator, class_code = (part.strip() for part in text.partition("="))
    if not separator or not name:
        raise argparse.ArgumentTypeError(f"科目名=クラス記号 の形にしてください: {text}")
    return name, class_code


def main() -> None:
    parser = argparse.ArgumentParser(description="道標を作って保存する、保存した道標を表示する")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create", help="職業と回生から道標を作って保存する")
    create.add_argument("occupation")
    create.add_argument("--grade", type=int, choices=sorted(ALL_GRADES), required=True)
    create.add_argument(
        "--term",
        choices=[term.value for term in Term],
        default=term_on(university_today()).value,
        help="始める学期(spring か autumn)。既定は今日の月から決める",
    )
    add_department_option(create)
    add_year_option(create)
    create.add_argument(
        "--class",
        dest="classes",
        type=_chosen_class,
        action="append",
        default=[],
        help="学科で分かれたクラスの選択。科目名=クラス記号 の形で、科目ごとに繰り返す。"
        "記号の無いクラスは 科目名= と書く",
    )
    show = commands.add_parser("show", help="保存した道標を表示する")
    show.add_argument("plan_id", type=UUID)
    args = parser.parse_args()
    if args.command == "create":
        chosen = [name for name, _ in args.classes]
        repeated = sorted({name for name in chosen if chosen.count(name) > 1})
        if repeated:
            parser.error(f"同じ科目のクラスを 2 回選んでいます: {'、'.join(repeated)}")

    settings = load_settings()
    engine = database_engine(settings)
    try:
        if args.command == "show":
            plan = SqlPlanRepository(engine).get(args.plan_id)
            if plan is None:
                sys.exit(f"Plan がありません: {args.plan_id}")
        else:
            requested = request_plan(settings, engine).run(
                SqlUserRepository(engine).id_of(CLI_SUBJECT),
                args.occupation,
                args.department,
                args.year,
                Semester(args.grade, Term(args.term)),
                dict(args.classes),
            )
            plan = build_plans(settings, engine).build(requested.id)
            if plan is None:
                sys.exit(f"ほかの worker が先に作り始めました: {requested.id}")
        print(render(plan))
        if plan.status is PlanStatus.FAILED:
            sys.exit(1)
    except (SearchError, RoadmapError, PlanError, PlanFormatError) as error:
        sys.exit(f"道標を止めました: {error}")
    except OperationalError as error:
        sys.exit(f"DB に接続できません: {error.orig}")
    except SQLAlchemyError as error:
        sys.exit(f"DB の操作に失敗しました: {error}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
