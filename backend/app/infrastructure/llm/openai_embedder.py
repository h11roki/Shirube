from typing import Self

from langchain_openai import OpenAIEmbeddings
from openai import OpenAIError
from pydantic import SecretStr

from app.application.ports import EmbeddingError


class OpenAIEmbedder:
    def __init__(self, client: OpenAIEmbeddings) -> None:
        self._client = client

    @classmethod
    def connect(
        cls, model: str, dimensions: int, api_key: SecretStr, timeout: float, retries: int
    ) -> Self:
        return cls(
            OpenAIEmbeddings(
                model=model,
                dimensions=dimensions,
                openai_api_key=api_key,
                request_timeout=timeout,
                max_retries=retries,
            )
        )

    @property
    def model(self) -> str:
        return self._client.model

    def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            return self._client.embed_documents(texts)
        except (OpenAIError, OSError) as error:
            raise EmbeddingError(f"埋め込みの API 呼び出しに失敗しました: {error}") from error
