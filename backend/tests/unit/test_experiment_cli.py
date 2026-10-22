from typing import Any

import pytest
from langchain_core.messages import HumanMessage

from app.application.ports import TokenUsage
from app.infrastructure.llm.usage_meter import LangChainUsageMeter
from app.presentation.cli.experiment import compare, unpriced, yen
from tests.fakes import chat_answering


def test_cost_counts_cached_input_at_its_own_price_and_matches_dated_model_names() -> None:
    usage = {"gpt-5.4-nano-2026-03-17": TokenUsage(1_000_000, 200_000, 100_000)}

    assert yen(usage) == pytest.approx((0.8 * 0.20 + 0.2 * 0.02 + 0.1 * 1.25) * 150)


def test_models_without_a_price_cost_nothing_and_are_listed() -> None:
    usage = {"gpt-5.4-mini": TokenUsage(1_000_000, 0, 0), "other-model": TokenUsage(5, 0, 5)}

    assert yen(usage) == pytest.approx(0.75 * 150)
    assert unpriced(usage) == ["other-model"]


def test_the_meter_reads_token_usage_from_langchain_by_model() -> None:
    chat = chat_answering({"content": "はい"})

    answer, usage = LangChainUsageMeter().metered(lambda: chat.invoke([HumanMessage("質問")]))

    assert answer.content == "はい"
    assert usage == {"test-model": TokenUsage(input=1, cached=0, output=1)}


def spread(value: float, std: float) -> dict[str, float]:
    return {"mean": value, "std": std, "low": value - std, "high": value + std}


def run(label: str, repeats: int, unrelated: float, std: float) -> dict[str, Any]:
    summary: dict[str, Any] = {
        key: spread(0.5, 0.0)
        for key in (
            "recall@10",
            "recall@20",
            "recall@30",
            "core_precision",
            "expected_as_core",
            "cores",
            "foundations",
        )
    }
    summary |= {
        "unrelated": spread(unrelated, std),
        "overlap": 0.6,
        "core_overlap": 0.7,
        "yen_per_plan": 1.5,
        "seconds": {"total": 12.0},
    }
    return {"label": label, "config": {"repeats": repeats}, "summary": summary}


def test_compare_tells_whether_a_difference_is_larger_than_the_spread() -> None:
    lines = compare(run("before", 3, 0.20, 0.02), run("after", 3, 0.10, 0.03)).splitlines()

    unrelated = next(line for line in lines if line.startswith("  選んだ科目のうち関係なし"))
    assert "差 -10.00 ポイント" in unrelated
    assert unrelated.endswith("揺れより大きい")
    precision = next(line for line in lines if line.startswith("  中心の適合率"))
    assert precision.endswith("揺れの範囲")


def test_compare_does_not_judge_the_spread_of_a_single_run() -> None:
    lines = compare(run("before", 1, 0.20, 0.0), run("after", 3, 0.10, 0.03)).splitlines()

    unrelated = next(line for line in lines if line.startswith("  選んだ科目のうち関係なし"))
    assert unrelated.endswith("、-")
