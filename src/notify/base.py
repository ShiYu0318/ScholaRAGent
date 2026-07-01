"""推送通道抽象層（Week9）。

各平台 adapter 實作同一介面，dispatcher 統一廣播。憑證缺漏時 enabled=False，
會被自動略過而非報錯，方便逐步開通各平台。
"""
from abc import ABC, abstractmethod

from src.utils.logger import get_logger


class Notifier(ABC):
    name = "notifier"

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    @property
    @abstractmethod
    def enabled(self):
        """是否已備妥必要憑證，可實際發送。"""

    @abstractmethod
    def send(self, text):
        """發送純文字訊息，回傳是否成功。"""
