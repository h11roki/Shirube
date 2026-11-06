import logging
import re
from collections.abc import Callable
from datetime import timedelta
from time import perf_counter
from typing import assert_never
from uuid import UUID

from app.application.ports import (
    BuildOutcome,
    CourseRepository,
    CourseSelectionError,
    EmbeddingError,
    FailureCause,
    OccupationAnalysisError,
    PlanBuild,
    PlanBuildLog,
    PlanRepository,
    UsageMeter,
    UserRepository,
)
from app.application.recommend_courses import Recommender, RecommendStep
from app.application.search_courses import NoCandidatesError
from app.domain.plan import Plan, PlanResult, PlanStage, PlanStatus
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
CAUSE_DEPTH = 8
CAUSE_CODE = re.compile(r"[a-z0-9_]{1,64}")

logger = logging.getLogger(__name__)


class BuildPlans:
    def __init__(
        self,
        recommend: Recommender,
        courses: CourseRepository,
        plans: PlanRepository,
        users: UserRepository,
        builds: PlanBuildLog,
        meter: UsageMeter,
        clock: Callable[[], float] = perf_counter,
    ) -> None:
        self._recommend = recommend
        self._courses = courses
        self._plans = plans
        self._users = users
        self._builds = builds
        self._meter = meter
        self._clock = clock

    def fail_stalled(self, after: timedelta) -> list[UUID]:
        stalled = self._plans.fail_stalled(after, STALLED)
        for plan_id in stalled:
            logger.warning("作成中のまま止まった道標を失敗にしました: %s", plan_id)
            self._record(plan_id, PlanBuild(BuildOutcome.STALLED))
        return stalled

    def build_next(self) -> Plan | None:
        claimed = self._plans.claim_next()
        return None if claimed is None else self._build(claimed)

    def build(self, plan_id: UUID) -> Plan | None:
        claimed = self._plans.claim(plan_id)
        return None if claimed is None else self._build(claimed)

    def _build(self, plan: Plan) -> Plan | None:
        conditions = plan.conditions
        entered = [(PlanStage.ANALYZING, self._clock())]
        cause: FailureCause | None = None
        with self._meter.meter() as usage:
            try:
                sections = self._courses.sections(conditions.year)
                recommendation = self._recommend.run(
                    conditions.occupation,
                    conditions.year,
                    conditions.department,
                    conditions.semesters,
                    lambda step: self._enter_step(plan, step, entered),
                    excluded=self._users.taken(plan.owner_id) | set(conditions.fixed_courses),
                )
                self._enter(plan, PlanStage.PLACING, entered)
                roadmap = conditions.roadmap(
                    recommendation,
                    sections,
                    page_of=(
                        self._courses.syllabus_codes(conditions.year)
                        if conditions.fixed_courses
                        else {}
                    ),
                )
                finished = plan.succeeded(PlanResult(recommendation, roadmap))
            except UPSTREAM_ERRORS as error:
                logger.exception("道標 %s の推薦で外部のサービスの呼び出しに失敗しました", plan.id)
                finished = plan.failed(UPSTREAM_FAILURE)
                cause = failure_cause(error)
            except NoCandidatesError as error:
                logger.warning("道標 %s の推薦の候補がありませんでした: %s", plan.id, error)
                finished = plan.failed(str(error))
                cause = failure_cause(error)
            except Exception as error:
                logger.exception("道標 %s を作れませんでした", plan.id)
                finished = plan.failed(SERVER_FAILURE)
                cause = failure_cause(error)
        ends = [mark for _, mark in entered[1:]] + [self._clock()]
        seconds: dict[PlanStage, float] = {}
        for (stage, start), end in zip(entered, ends, strict=True):
            seconds[stage] = seconds.get(stage, 0.0) + end - start
        saved = self._plans.finish(finished)
        if not saved:
            outcome = BuildOutcome.DISCARDED
        elif finished.status is PlanStatus.SUCCEEDED:
            outcome = BuildOutcome.SUCCEEDED
        else:
            outcome = BuildOutcome.FAILED
        try:
            spent = usage()
        except Exception:
            logger.exception("道標 %s で使ったトークンを読めませんでした", plan.id)
            spent = {}
        self._record(plan.id, PlanBuild(outcome, cause, seconds, spent))
        if saved:
            return finished
        logger.warning("道標 %s は作っている間に作成中でなくなったので、結果を捨てました", plan.id)
        return self._plans.get(plan.id)

    def _enter_step(
        self, plan: Plan, step: RecommendStep, entered: list[tuple[PlanStage, float]]
    ) -> None:
        match step:
            case RecommendStep.SEARCHING:
                self._enter(plan, PlanStage.SEARCHING, entered)
            case RecommendStep.SELECTING:
                self._enter(plan, PlanStage.SELECTING, entered)
            case _:
                assert_never(step)

    def _enter(self, plan: Plan, stage: PlanStage, entered: list[tuple[PlanStage, float]]) -> None:
        entered.append((stage, self._clock()))
        try:
            self._plans.enter_stage(plan.id, stage)
        except Exception:
            logger.exception("道標 %s の段 %s を書けませんでした", plan.id, stage)

    def _record(self, plan_id: UUID, build: PlanBuild) -> None:
        try:
            self._builds.record(plan_id, build)
        except Exception:
            logger.exception("道標 %s を作った記録を書けませんでした", plan_id)


def failure_cause(error: BaseException) -> FailureCause:
    chain = [error]
    while len(chain) < CAUSE_DEPTH:
        last = chain[-1]
        reason = last.__cause__ or (None if last.__suppress_context__ else last.__context__)
        if reason is None:
            break
        chain.append(reason)
    codes = (getattr(link, "code", None) for link in reversed(chain))
    return FailureCause(
        tuple(type(link).__name__ for link in chain),
        next(
            (code for code in codes if isinstance(code, str) and CAUSE_CODE.fullmatch(code)), None
        ),
    )
