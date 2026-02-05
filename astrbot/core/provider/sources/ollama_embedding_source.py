import aiohttp

from ..entities import ProviderType
from ..provider import EmbeddingProvider
from ..register import register_provider_adapter


@register_provider_adapter(
    "ollama_embedding",
    "Ollama 嵌入提供商适配器",
    provider_type=ProviderType.EMBEDDING,
)
class OllamaEmbeddingProvider(EmbeddingProvider):
    """Ollama 本地嵌入提供商"""

    def __init__(self, provider_config: dict, provider_settings: dict) -> None:
        super().__init__(provider_config, provider_settings)
        api_base: str = provider_config.get("embedding_api_base", "http://localhost:11434")
        if api_base.endswith("/"):
            api_base = api_base[:-1]
        self.api_base = api_base
        self.model: str = provider_config.get("embedding_model", "nomic-embed-text")

    async def _request(self, prompt: str) -> dict:
        """发起 API 请求"""
        payload = {
            "model": self.model,
            "prompt": prompt,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_base}/api/embeddings",
                json=payload,
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Ollama API 请求失败 ({response.status}): {error_text}")
                return await response.json()

    async def get_embedding(self, text: str) -> list[float]:
        """获取单个文本的嵌入"""
        response = await self._request(text)
        embedding = response.get("embedding")
        if embedding is None:
            raise Exception("Ollama API 返回数据中没有 embedding 字段")
        return embedding

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """批量获取文本的嵌入"""
        # Ollama 的嵌入 API 不支持批量，需要逐个请求
        embeddings = []
        for text in texts:
            embedding = await self.get_embedding(text)
            embeddings.append(embedding)
        return embeddings

    def get_dim(self) -> int:
        """获取向量的维度"""
        return int(self.provider_config.get("embedding_dimensions", 768))
