import asyncio
from datetime import datetime
from src.crawlers.arxiv_crawler import ArxivCrawler
from src.utils.logger import get_logger

logger = get_logger("Main")

async def main():
    # 初始化爬蟲
    crawler = ArxivCrawler(headless=True)
    
    # 抓取資料
    limit = 10
    results = await crawler.fetch_latest_papers(limit=limit)
    
    if not results:
        logger.error("未抓取到任何資料。")
        return

    # 準備存檔路徑
    # 檔名範例：data/arxiv_20260308_0700.txt
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    file_path = f"data/arxiv_{timestamp}.txt"

    # 寫入檔案與格式化輸出
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"AIR Agent 抓取報告 ({timestamp})\n")
            f.write(f"來源: arXiv (cs.AI)\n")
            f.write(f"數量: {len(results)}\n")
            f.write("-" * 50 + "\n\n")

            for i, p in enumerate(results, 1):
                content = f"[{i}] {p['title']}\n    連結: {p['link']}\n"
                
                # 同時印出到終端機與寫入檔案
                print(content.strip())
                f.write(content + "\n")
                
        logger.info(f"資料已成功存入: {file_path}")
        
    except Exception as e:
        logger.error(f"存檔失敗: {e}")

if __name__ == "__main__":
    asyncio.run(main())