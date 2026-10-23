from collections.abc import Callable, Iterator
from contextlib import contextmanager

from langchain_core.callbacks import get_usage_metadata_callback

from app.application.ports import TokenUsage


class LangChainUsageMeter:
    @contextmanager
    def meter(self) -> Iterator[Callable[[], dict[str, TokenUsage]]]:
        with get_usage_metadata_callback() as callback:
            yield lambda: {
                model: TokenUsage(
                    usage["input_tokens"],
                    usage.get("input_token_details", {}).get("cache_read", 0),
                    usage["output_tokens"],
                )
                for model, usage in callback.usage_metadata.items()
            }
