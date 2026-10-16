import httpx
import pytest
from langchain_openai import OpenAIEmbeddings
from pydantic import SecretStr

from app.application.ports import EmbeddingError
from app.infrastructure.llm.openai_embedder import OpenAIEmbedder


def test_a_failed_api_call_is_an_embedding_error() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400, json={"error": {"message": "失敗", "type": "invalid_request_error"}}
        )

    client = OpenAIEmbeddings(
        model="test-model",
        openai_api_key=SecretStr("test-key"),
        check_embedding_ctx_length=False,
        http_client=httpx.Client(transport=httpx.MockTransport(respond)),
    )

    with pytest.raises(EmbeddingError, match="埋め込みの API 呼び出しに失敗しました"):
        OpenAIEmbedder("test-model", client).embed(["本文"])
