from playwright.async_api import async_playwright
from src.utils.logger import get_logger

class BaseCrawler:
    def __init__(self, headless=True):
        self.headless = headless
        self.logger = get_logger(self.__class__.__name__)

    async def run_with_page(self, url, callback):
        async with async_playwright() as p:
            self.logger.info(f"啟動瀏覽器 (headless={self.headless})...")
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            try:
                self.logger.info(f"正在存取: {url}")
                await page.goto(url, timeout=60000)
                return await callback(page)
            except Exception as e:
                self.logger.error(f"執行時發生錯誤: {e}", exc_info=True)
                return None
            finally:
                await browser.close()
                self.logger.info("瀏覽器已關閉")