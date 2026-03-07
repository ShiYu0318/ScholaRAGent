import asyncio
from src.crawlers.arxiv_crawler import ArxivCrawler
from src.utils.file_manager import save_to_text
from src.utils.logger import get_logger

logger = get_logger("Main")

async def main():
    crawler = ArxivCrawler(headless=True)
    
    logger.info("抓取 arXiv 最新論文")
    papers = await crawler.fetch_latest_papers(limit=50)
    
    if not papers:
        logger.warning("未取得任何資料")
        return

    save_to_text(papers, source_name="arxiv")
    
    logger.info("執行完畢")

if __name__ == "__main__":
    asyncio.run(main())