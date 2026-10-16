import argparse
import sys

from openai import OpenAIError
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.application.ports import CourseSelectionError, OccupationAnalysisError
from app.application.recommend_courses import RecommendCourses
from app.application.search_courses import SearchCourses, SearchError
from app.domain.course import ALL_GRADES
from app.domain.recommendation import (
    Recommendation,
    RecommendationError,
    Relevance,
)
from app.infrastructure.db.chunks import SqlChunkRepository
from app.infrastructure.db.courses import SqlCourseRepository
from app.presentation.cli.environment import (
    database_engine,
    load_settings,
    openai_course_selector,
    openai_embedder,
    openai_occupation_analyzer,
)
from app.presentation.cli.labels import RELEVANCE_LABELS, with_prerequisite
from app.presentation.cli.options import add_year_option

DEFAULT_DEPARTMENT = "情"


def render(recommendation: Recommendation) -> str:
    profile = recommendation.profile
    lines = [f"職業: {profile.occupation} → {profile.interpretation}"]
    if profile.assumption is not None:
        lines.append(f"前提: {profile.assumption}")
    lines.append(f"スキル: {' / '.join(profile.skills)}")
    for relevance in Relevance:
        courses = [course for course in recommendation.courses if course.relevance is relevance]
        lines.append(f"{RELEVANCE_LABELS[relevance]} {len(courses)} 科目")
        lines += [
            f"  {with_prerequisite(course.name, course.prerequisite_for)}: {course.reason}"
            for course in courses
        ]
    if recommendation.unlinked:
        unlinked = [
            with_prerequisite(choice.name, choice.prerequisite_for)
            for choice in recommendation.unlinked
        ]
        lines.append(f"中心につながらず外した土台: {'、'.join(unlinked)}")
    lines.append(f"検索の上位 {len(recommendation.candidates)} 件から選んだ")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="職業から取るべき科目と理由を推薦する")
    parser.add_argument("occupation")
    add_year_option(parser)
    parser.add_argument("--department", default=DEFAULT_DEPARTMENT)
    parser.add_argument(
        "--grades", type=int, nargs="+", choices=sorted(ALL_GRADES), default=sorted(ALL_GRADES)
    )
    args = parser.parse_args()

    settings = load_settings()
    embedder = openai_embedder(settings)
    analyzer = openai_occupation_analyzer(settings)
    selector = openai_course_selector(settings)
    engine = database_engine(settings)
    courses = SqlCourseRepository(engine)
    search = SearchCourses(courses, SqlChunkRepository(engine), embedder)
    recommend = RecommendCourses(
        search, courses, analyzer, selector, settings.selection_candidate_limit
    )
    try:
        grades = set(args.grades)
        print(render(recommend.run(args.occupation, args.year, args.department, grades)))
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
