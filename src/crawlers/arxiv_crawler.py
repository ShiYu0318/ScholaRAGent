from playwright.async_api import async_playwright
from src.utils.logger import get_logger

logger = get_logger("ArxivCrawler")

class ArxivCrawler:
    def __init__(self, headless=True):
        self.headless = headless
        self.url = "https://arxiv.org/list/cs.AI/recent"

    async def fetch_latest_papers(self, limit=5):
        async with async_playwright() as p:
            logger.info(f"啟動瀏覽器 (headless={self.headless})...")
            browser = await p.chromium.launch(headless=self.headless)
            page = await browser.new_page()
            
            try:
                logger.info(f"正在存取: {self.url}")
                await page.goto(self.url, timeout=60000)
                await page.wait_for_selector("#dlpage")
                
                dts = await page.locator("dt").all()
                dds = await page.locator("dd").all()
                
                papers = []
                for i in range(min(len(dts), limit)):
                    title_elem = dds[i].locator(".list-title")
                    title = (await title_elem.inner_text()).replace("Title:", "").strip()
                    
                    link_elem = dts[i].locator("a[title='Abstract']")
                    link_suffix = await link_elem.get_attribute("href")
                    link = f"https://arxiv.org{link_suffix}"
                    
                    papers.append({"title": title, "link": link})
                    logger.debug(f"抓取到論文: {title[:30]}...")
                
                logger.info(f"抓取完成，共 {len(papers)} 筆數據")
                return papers
            except Exception as e:
                logger.error(f"爬蟲發生錯誤: {str(e)}", exc_info=True)
                return []
            finally:
                await browser.close()