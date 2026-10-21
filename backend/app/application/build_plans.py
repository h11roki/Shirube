import logging
from datetime import datetime, timedelta
from typing import assert_never
from uuid import UUID

from app.application.ports import (
    CourseRepository,
    CourseSelectionError,
    EmbeddingError,
    OccupationAnalysisError,
    PlanRepository,
    UserRepository,
)
from app.application.recommend_courses import RecommendCourses, RecommendStep
from app.application.search_courses import NoCandidatesError
from app.domain.plan import Plan, PlanResult, PlanStage
from app.domain.quota import day_start
from app.domain.recommendation import RecommendationError

UPSTREAM_FAILURE = "推薦に使う外部のサービスの呼び出しに失敗しました"
STALLED = "道標を作る途中で止まりました"
SERVER_FAILURE = "サーバーで道標を扱えませんでした"
UPSTREAM_ERRORS: tuple[type[Exception], ...] = (
    EmbeddingError,
    OccupationAnalysisError,
    CourseSelectionError,
    RecommendationError,
)

logger = logging.getLogger(__name__)


class BuildPlans:
    def __init__(
        self,
        recommend: RecommendCourses,
        courses: CourseRepository,
        plans: PlanRepository,
        users: UserRepository,
    ) -> None:
        self._recommend = recommend
        self._courses = courses
        self._plans = plans
        self._users = users
        self._forgotten_before: datetime | None = None

    def fail_stalled(self, after: timedelta) -> list[UUID]:
        stalled = self._plans.fail_stalled(after, STALLED)
        for plan_id in stalled:
            logger.warning("作成中のまま止まった道標を失敗にしました: %s", plan_id)
        return stalled

    def forget_deleted(self, now: datetime) -> None:
        before = day_start(now)
        if before == self._forgotten_before:
            return
        self._forgotten_before = before
        purged = self._plans.purge_deleted(before)
        if purged:
            logger.info("前の日までに削除した道標 %d 件の日時を消しました", purged)

    def build_next(self) -> Plan | None:
        claimed = self._plans.claim_next()
        return None if claimed is None else self._build(claimed)

    def build(self, plan_id: UUID) -> Plan | None:
        claimed = self._plans.claim(plan_id)
        return None if claimed is None else self._build(claimed)

    def _build(self, plan: Plan) -> Plan | None:
        conditions = plan.conditions
        try:
            sections = self._courses.sections(conditions.year)
            recommendation = self._recommend.run(
                conditions.occupation,
                conditions.year,
                conditions.department,
                conditions.semesters,
                lambda step: self._enter_step(plan, step),
                excluded=self._users.taken(plan.owner_id),
            )
            self._enter(plan, PlanStage.PLACING)
            roadmap = conditions.roadmap(recommendation, sections)
            finished = plan.succeeded(PlanResult(recommendation, roadmap))
        except UPSTREAM_ERRORS:
            logger.exception("道標 %s の推薦で外部のサービスの呼び出しに失敗しました", plan.id)
            finished = plan.failed(UPSTREAM_FAILURE)
        except NoCandidatesError as error:
            logger.warning("道標 %s の推薦の候補がありませんでした: %s", plan.id, error)
            finished = plan.failed(str(error))
        except Exception:
            logger.exception("道標 %s を作れませんでした", plan.id)
            finished = plan.failed(SERVER_FAILURE)
        if self._plans.finish(finished):
            return finished
        logger.warning("道標 %s は作っている間に作成中でなくなったので、結果を捨てました", plan.id)
        return self._plans.get(plan.id)

    def _enter_step(self, plan: Plan, step: RecommendStep) -> None:
        match step:
            case RecommendStep.SEARCHING:
                self._enter(plan, PlanStage.SEARCHING)
            case RecommendStep.SELECTING:
                self._enter(plan, PlanStage.SELECTING)
            case _:
                assert_never(step)

    def _enter(self, plan: Plan, stage: PlanStage) -> None:
        try:
            self._plans.enter_stage(plan.id, stage)
        except Exception:
            logger.exception("道標 %s の段 %s を書けませんでした", plan.id, stage)
