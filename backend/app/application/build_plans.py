import logging
from datetime import timedelta
from uuid import UUID

from app.application.ports import (
    CourseRepository,
    CourseSelectionError,
    EmbeddingError,
    OccupationAnalysisError,
    PlanRepository,
)
from app.application.recommend_courses import RecommendCourses, RecommendStep
from app.domain.plan import Plan, PlanResult, PlanStage
from app.domain.recommendation import RecommendationError
from app.domain.roadmap import place, remaining_semesters

UPSTREAM_FAILURE = "推薦に使う外部のサービスの呼び出しに失敗しました"
STALLED = "道標を作る途中で止まりました"
SERVER_FAILURE = "サーバーで道標を扱えませんでした"
STAGE_OF_STEP = {
    RecommendStep.SEARCHING: PlanStage.SEARCHING,
    RecommendStep.SELECTING: PlanStage.SELECTING,
}
UPSTREAM_ERRORS: tuple[type[Exception], ...] = (
    EmbeddingError,
    OccupationAnalysisError,
    CourseSelectionError,
    RecommendationError,
)

logger = logging.getLogger(__name__)


class BuildPlans:
    def __init__(
        self, recommend: RecommendCourses, courses: CourseRepository, plans: PlanRepository
    ) -> None:
        self._recommend = recommend
        self._courses = courses
        self._plans = plans

    def fail_stalled(self, after: timedelta) -> list[UUID]:
        stalled = self._plans.fail_stalled(after, STALLED)
        for plan_id in stalled:
            logger.warning("作成中のまま止まった道標を失敗にしました: %s", plan_id)
        return stalled

    def build_next(self) -> Plan | None:
        claimed = self._plans.claim_next()
        return None if claimed is None else self._build(claimed)

    def build(self, plan_id: UUID) -> Plan | None:
        claimed = self._plans.claim(plan_id)
        return None if claimed is None else self._build(claimed)

    def _build(self, plan: Plan) -> Plan | None:
        conditions = plan.conditions
        try:
            semesters = remaining_semesters(conditions.start)
            sections = self._courses.sections(conditions.year)
            recommendation = self._recommend.run(
                conditions.occupation,
                conditions.year,
                conditions.department,
                semesters,
                lambda step: self._enter(plan, STAGE_OF_STEP[step]),
            )
            self._enter(plan, PlanStage.PLACING)
            roadmap = place(
                recommendation,
                sections,
                conditions.department,
                conditions.year,
                semesters,
                conditions.credit_limit,
                dict(conditions.chosen_classes),
            )
            finished = plan.succeeded(PlanResult(recommendation, roadmap))
        except UPSTREAM_ERRORS:
            logger.exception("道標 %s の推薦で外部のサービスの呼び出しに失敗しました", plan.id)
            finished = plan.failed(UPSTREAM_FAILURE)
        except Exception:
            logger.exception("道標 %s を作れませんでした", plan.id)
            finished = plan.failed(SERVER_FAILURE)
        if self._plans.finish(finished):
            return finished
        logger.warning("道標 %s は作っている間に作成中でなくなったので、結果を捨てました", plan.id)
        return self._plans.get(plan.id)

    def _enter(self, plan: Plan, stage: PlanStage) -> None:
        try:
            self._plans.enter_stage(plan.id, stage)
        except Exception:
            logger.warning("道標 %s の段 %s を書けませんでした", plan.id, stage, exc_info=True)
