from playwright.async_api import async_playwright

class BaseCrawler:
    def __init__(self, headless=True):
        self.headless = headless

    async def get_page_content(self, url, wait_selector=None):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            try:
                await page.goto(url, timeout=60000)
                if wait_selector:
                    await page.wait_for_selector(wait_selector)
                content = await page.content()
                return content
            except Exception as e:
                print(f"Error crawling {url}: {e}")
                return None
            finally:
                await browser.close()