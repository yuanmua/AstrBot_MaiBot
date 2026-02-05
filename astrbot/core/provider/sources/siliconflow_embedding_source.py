import aiohttp

from ..entities import ProviderType
from ..provider import EmbeddingProvider
from ..register import register_provider_adapter


@register_provider_adapter(
    "siliconflow_embedding",
    "SiliconFlow 嵌入提供商适配器",
    provider_type=ProviderType.EMBEDDING,
)
class SiliconFlowEmbeddingProvider(EmbeddingProvider):
    """SiliconFlow 嵌入提供商"""

    def __init__(self, provider_config: dict, provider_settings: dict) -> None:
        super().__init__(provider_config, provider_settings)
        self.api_key: str = provider_config["embedding_api_key"]
        api_base: str = provider_config.get(
            "embedding_api_base",
            "https://api.siliconflow.cn/v1",
        )
        if api_base.endswith("/"):
            api_base = api_base[:-1]
        self.api_base = api_base
        self.model: str = provider_config.get("embedding_model", "BAAI/bge-large-zh-v1.5")

    async def _request(self, input_text: str | list[str]) -> dict:
        """发起 API 请求"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "input": input_text,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_base}/embeddings",
                headers=headers,
                json=payload,
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"SiliconFlow API 请求失败 ({response.status}): {error_text}")
                return await response.json()

    async def get_embedding(self, text: str) -> list[float]:
        """获取单个文本的嵌入"""
        response = await self._request(text)
        data = response.get("data", [])
        if not data:
            raise Exception("SiliconFlow API 返回数据为空")
        return data[0]["embedding"]

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """批量获取文本的嵌入"""
        response = await self._request(texts)
        data = response.get("data", [])
        return [item["embedding"] for item in data]

    def get_dim(self) -> int:
        """获取向量的维度"""
        return int(self.provider_config.get("embedding_dimensions", 1024))
