"""sentence-transformers 包裝，產生正規化向量供 FAISS 內積檢索。"""
from sentence_transformers import SentenceTransformer

from src import config
from src.utils.logger import get_logger


class Embedder:
    def __init__(self, model_name=None):
        self.logger = get_logger(self.__class__.__name__)
        name = model_name or config.EMBED_MODEL
        self.logger.info(f"載入 embedding 模型: {name}")
        self.model = SentenceTransformer(name)
        # 不同版本方法名不同，直接由一次 encode 取得維度最穩當
        self.dim = int(self.model.encode(["dim probe"]).shape[1])

    def encode(self, texts):
        """回傳 float32、L2 正規化後的向量 (n, dim)。"""
        return self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).astype("float32")
