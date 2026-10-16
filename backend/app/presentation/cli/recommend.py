import argparse
import sys

from openai import OpenAIError
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.application.ports import CourseSelectionError, OccupationAnalysisError
from app.application.search_courses import SearchError
from app.domain.course import ALL_GRADES
from app.domain.recommendation import (
    Recommendation,
    RecommendationError,
    Relevance,
)
from app.domain.roadmap import ALL_SEMESTERS
from app.presentation.cli.labels import (
    RELEVANCE_LABELS,
    profile_lines,
    unlinked_lines,
    with_prerequisite,
)
from app.presentation.cli.options import add_department_option, add_year_option
from app.presentation.composition import database_engine, load_settings, recommend_courses


def render(recommendation: Recommendation) -> str:
    lines = profile_lines(recommendation.profile)
    for relevance in Relevance:
        courses = [course for course in recommendation.courses if course.relevance is relevance]
        lines.append(f"{RELEVANCE_LABELS[relevance]} {len(courses)} 科目")
        lines += [
            f"  {with_prerequisite(course.name, course.prerequisite_for)}: {course.reason}"
            for course in courses
        ]
    lines += unlinked_lines(recommendation.unlinked)
    lines.append(f"検索の上位 {len(recommendation.candidates)} 件から選んだ")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="職業から取るべき科目と理由を推薦する")
    parser.add_argument("occupation")
    add_year_option(parser)
    add_department_option(parser)
    parser.add_argument(
        "--grades", type=int, nargs="+", choices=sorted(ALL_GRADES), default=sorted(ALL_GRADES)
    )
    args = parser.parse_args()

    settings = load_settings()
    engine = database_engine(settings)
    recommend = recommend_courses(settings, engine)
    try:
        semesters = [semester for semester in ALL_SEMESTERS if semester.grade in args.grades]
        print(render(recommend.run(args.occupation, args.year, args.department, semesters)))
    except (
        SearchError,
        OccupationAnalysisError,
        CourseSelectionError,
        RecommendationError,
    ) as error:
        sys.exit(f"推薦を止めました: {error}")
    except OperationalError as error:
        sys.exit(f"DB に接続できません: {error.orig}")
    except SQLAlchemyError as error:
        sys.exit(f"DB の操作に失敗しました: {error}")
    except OpenAIError as error:
        sys.exit(f"OpenAI の API 呼び出しに失敗しました: {error}")
    except OSError as error:
        sys.exit(f"ネットワークに失敗しました: {error}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
