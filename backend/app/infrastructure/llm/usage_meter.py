from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from threading import Lock

from langchain_core.callbacks import UsageMetadataCallbackHandler
from langchain_core.tracers.context import register_configure_hook

from app.application.ports import TokenUsage

METER_DEPTH = ContextVar("shirube_usage_depth", default=0)
METER_LEVELS: list[ContextVar[UsageMetadataCallbackHandler | None]] = []
METER_LEVELS_LOCK = Lock()


def _level(depth: int) -> ContextVar[UsageMetadataCallbackHandler | None]:
    with METER_LEVELS_LOCK:
        while len(METER_LEVELS) <= depth:
            level: ContextVar[UsageMetadataCallbackHandler | None] = ContextVar(
                f"shirube_usage_{len(METER_LEVELS)}", default=None
            )
            register_configure_hook(level, inheritable=True)
            METER_LEVELS.append(level)
        return METER_LEVELS[depth]


class LangChainUsageMeter:
    @contextmanager
    def meter(self) -> Iterator[Callable[[], dict[str, TokenUsage]]]:
        depth = METER_DEPTH.get()
        level = _level(depth)
        handler = UsageMetadataCallbackHandler()
        handler_token = level.set(handler)
        depth_token = METER_DEPTH.set(depth + 1)
        try:
            yield lambda: {
                model: TokenUsage(
                    usage["input_tokens"],
                    usage.get("input_token_details", {}).get("cache_read", 0),
                    usage["output_tokens"],
                )
                for model, usage in handler.usage_metadata.items()
            }
        finally:
            METER_DEPTH.reset(depth_token)
            level.reset(handler_token)
