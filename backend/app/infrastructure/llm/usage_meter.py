from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from langchain_core.callbacks import UsageMetadataCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_core.tracers.context import register_configure_hook

from app.application.ports import TokenUsage


class _NestedUsage(UsageMetadataCallbackHandler):
    def __init__(self, outer: UsageMetadataCallbackHandler | None) -> None:
        super().__init__()
        self._outer = outer

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        super().on_llm_end(response, **kwargs)
        if self._outer is not None:
            self._outer.on_llm_end(response, **kwargs)


CURRENT_USAGE: ContextVar[UsageMetadataCallbackHandler | None] = ContextVar(
    "shirube_usage", default=None
)
register_configure_hook(CURRENT_USAGE, inheritable=True)


class LangChainUsageMeter:
    @contextmanager
    def meter(self) -> Iterator[Callable[[], dict[str, TokenUsage]]]:
        handler = _NestedUsage(CURRENT_USAGE.get())
        token = CURRENT_USAGE.set(handler)
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
            CURRENT_USAGE.reset(token)
