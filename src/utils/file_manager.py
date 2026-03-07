from datetime import datetime
from src.utils.logger import get_logger

logger = get_logger("FileManager")

def save_to_text(data, source_name="arxiv"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    file_path = f"data/{source_name}_{timestamp}.txt"
    
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"{source_name.upper()} 抓取報告 ({timestamp}) \n")
            f.write(f"數量: {len(data)}\n")
            f.write("-" * 50 + "\n\n")

            for i, item in enumerate(data, 1):
                f.write(f"[{i}] {item['title']}\n    連結: {item['link']}\n\n")
                
        logger.info(f"檔案已儲存至: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"存檔發生錯誤: {e}")
        return None