from playwright.async_api import async_playwright
from src.utils.logger import get_logger

class BaseCrawler:
    def __init__(self, headless=True):
        self.headless = headless
        self.logger = get_logger(self.__class__.__name__) # 自動抓取子類別的名字當 Logger 名稱

    async def run_with_page(self, url, callback):
        """
        負責開啟瀏覽器，執行完 callback 後自動關閉
        """
        async with async_playwright() as p:
            self.logger.info(f"啟動瀏覽器 (headless={self.headless})...")
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36..."
            )
            page = await context.new_page()
            
            try:
                self.logger.info(f"正在存取: {url}")
                await page.goto(url, timeout=60000)
                # 把 page 丟給子類別去操作
                return await callback(page)
            except Exception as e:
                self.logger.error(f"執行時發生錯誤: {e}", exc_info=True)
                return None
            finally:
                await browser.close()
                self.logger.info("瀏覽器已關閉")