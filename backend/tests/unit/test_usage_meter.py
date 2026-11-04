import pytest
from langchain_core.messages import HumanMessage
from langchain_core.tracers import context as langchain_context

from app.application.ports import TokenUsage
from app.infrastructure.llm.usage_meter import LangChainUsageMeter
from tests.fakes import chat_answering


def test_the_meter_reads_token_usage_from_langchain_by_model() -> None:
    chat = chat_answering({"content": "はい"})

    with LangChainUsageMeter().meter() as usage:
        answer = chat.invoke([HumanMessage("質問")])

    assert answer.content == "はい"
    assert usage() == {"test-model": TokenUsage(input=1, cached=0, output=1)}


def test_the_meter_keeps_the_usage_of_a_call_that_failed_afterwards() -> None:
    chat = chat_answering({"content": "はい"})

    with pytest.raises(RuntimeError), LangChainUsageMeter().meter() as usage:
        chat.invoke([HumanMessage("質問")])
        raise RuntimeError("答えを使えない")

    assert usage() == {"test-model": TokenUsage(input=1, cached=0, output=1)}


def test_an_outer_meter_also_counts_the_calls_of_an_inner_one_that_was_interrupted() -> None:
    chat = chat_answering({"content": "はい"})
    meter = LangChainUsageMeter()

    with meter.meter() as outer:
        with pytest.raises(KeyboardInterrupt), meter.meter() as inner:
            chat.invoke([HumanMessage("質問")])
            raise KeyboardInterrupt
        chat.invoke([HumanMessage("質問")])

    assert inner() == {"test-model": TokenUsage(input=1, cached=0, output=1)}
    assert outer() == {"test-model": TokenUsage(input=2, cached=0, output=2)}


def test_metering_again_and_again_adds_no_langchain_hooks() -> None:
    chat = chat_answering({"content": "はい"})
    meter = LangChainUsageMeter()
    hooks = len(langchain_context._configure_hooks)

    for _ in range(3):
        with meter.meter():
            chat.invoke([HumanMessage("質問")])

    assert len(langchain_context._configure_hooks) == hooks
