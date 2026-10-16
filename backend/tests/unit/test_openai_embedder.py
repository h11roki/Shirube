from typing import Any

import pytest
from langchain_openai import OpenAIEmbeddings
from pydantic import SecretStr

from app.application.ports import EmbeddingError
from app.infrastructure.llm.openai_embedder import OpenAIEmbedder
from tests.fakes import failing_http_client


def embeddings(status: int) -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model="test-model",
        openai_api_key=SecretStr("test-key"),
        check_embedding_ctx_length=False,
        http_client=failing_http_client(status),
    )


def test_the_model_name_is_the_one_the_client_embeds_with() -> None:
    assert OpenAIEmbedder(embeddings(400)).model == "test-model"


def test_a_failed_api_call_is_an_embedding_error() -> None:
    with pytest.raises(EmbeddingError, match="埋め込みの API 呼び出しに失敗しました"):
        OpenAIEmbedder(embeddings(400)).embed(["本文"])


def test_a_failed_download_before_the_api_call_is_an_embedding_error() -> None:
    class Unreachable(OpenAIEmbeddings):
        def embed_documents(
            self, texts: list[str], chunk_size: int | None = None, **kwargs: Any
        ) -> list[list[float]]:
            raise ConnectionError("トークナイザを取得できない")

    client = Unreachable(model="test-model", openai_api_key=SecretStr("test-key"))

    with pytest.raises(EmbeddingError, match="トークナイザを取得できない"):
        OpenAIEmbedder(client).embed(["本文"])
