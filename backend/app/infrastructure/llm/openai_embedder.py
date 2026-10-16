from typing import Self

from langchain_openai import OpenAIEmbeddings
from openai import OpenAIError
from pydantic import SecretStr

from app.application.ports import EmbeddingError


class OpenAIEmbedder:
    def __init__(self, model: str, client: OpenAIEmbeddings) -> None:
        self._model = model
        self._client = client

    @classmethod
    def connect(cls, model: str, dimensions: int, api_key: SecretStr) -> Self:
        return cls(
            model, OpenAIEmbeddings(model=model, dimensions=dimensions, openai_api_key=api_key)
        )

    @property
    def model(self) -> str:
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            return self._client.embed_documents(texts)
        except OpenAIError as error:
            raise EmbeddingError(f"埋め込みの API 呼び出しに失敗しました: {error}") from error
