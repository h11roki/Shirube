from langchain_openai import OpenAIEmbeddings
from pydantic import SecretStr


class OpenAIEmbedder:
    def __init__(self, model: str, dimensions: int, api_key: SecretStr) -> None:
        self._model = model
        self._client = OpenAIEmbeddings(model=model, dimensions=dimensions, openai_api_key=api_key)

    @property
    def model(self) -> str:
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self._client.embed_documents(texts)
