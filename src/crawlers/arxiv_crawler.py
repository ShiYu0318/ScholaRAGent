from .base_crawler import BaseCrawler
import time
class ArxivCrawler(BaseCrawler):
    def __init__(self, headless=True):
        super().__init__(headless=headless)
        self.url = "https://arxiv.org/list/cs.AI/recent"

    async def fetch_latest_papers(self, limit=5):
        async def parser(page):
            await page.wait_for_selector("#dlpage")
            dts = await page.locator("dt").all()
            dds = await page.locator("dd").all()
            
            papers = []
            for i in range(min(len(dts), limit)):
                time.sleep(0.1)
                title = (await dds[i].locator(".list-title").inner_text()).replace("Title:", "").strip()
                link_suffix = await dts[i].locator("a[title='Abstract']").get_attribute("href")
                papers.append({
                    "title": title,
                    "link": f"https://arxiv.org{link_suffix}"
                })
            return papers

        return await self.run_with_page(self.url, parser)