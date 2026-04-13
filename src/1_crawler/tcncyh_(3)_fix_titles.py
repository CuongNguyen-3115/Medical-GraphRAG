import os
import json
import logging
import time
import requests
from bs4 import BeautifulSoup

# --- Cấu hình đường dẫn ---
BASE_DIR = r"C:\1. Project\2. DoAn_GraphRAG"
DATA_DIR = os.path.join(BASE_DIR, "Data")
LOG_DIR = os.path.join(BASE_DIR, "logs")
# File cần sửa là bản ghi (2026_3)
TARGET_FILE = os.path.join(DATA_DIR, "(2026_3)_tcncyh_all_medical_urls.json")

# Tạo thư mục logs nếu chưa có
os.makedirs(LOG_DIR, exist_ok=True)

# --- Khởi tạo Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "fix_titles_2026_3.log"), encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def get_correct_title(article_view_url):
    """Truy cập trang web và lấy title chính xác bằng cách thu hẹp phạm vi tìm kiếm"""
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(article_view_url, headers=headers, timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 1. Tìm khu vực chứa nội dung chính (Bỏ qua sidebar và navbar)
        # Chúng ta tìm div có class là 'article-details'
        main_content = soup.find('div', class_='col-md-8 article-details')
        
        if main_content:
            # 2. Chỉ tìm h2 nằm trong khu vực main_content này
            # Cấu trúc: <div class="article-details"> -> <header> -> <h2>
            title_tag = main_content.find('h2')
            
            if title_tag:
                # Trả về text và xóa các khoảng trắng thừa
                return title_tag.get_text(strip=True)
            
        logging.warning(f"Không tìm thấy thẻ h2 trong div.article-details tại {article_view_url}")
        return "N/A"
    
    except Exception as e:
        logging.error(f"Lỗi khi truy cập {article_view_url}: {e}")
        return None

def main():
    if not os.path.exists(TARGET_FILE):
        logging.error(f"Không tìm thấy file mục tiêu: {TARGET_FILE}")
        return

    # 1. Đọc dữ liệu JSON cũ
    with open(TARGET_FILE, 'r', encoding='utf-8') as f:
        data_list = json.load(f)

    logging.info(f"Bắt đầu cập nhật title cho {len(data_list)} bản ghi...")

    # 2. Duyệt và cập nhật
    updated_count = 0
    for idx, item in enumerate(data_list):
        # Vì 'url' hiện tại là link PDF (.../view/4816/3188)
        # Chúng ta cần link bài báo (.../view/4816) để lấy HTML
        pdf_url = item.get('url', '')
        if pdf_url and "/view/" in pdf_url:
            # Tách lấy phần link bài báo (bỏ phần ID PDF cuối cùng)
            article_view_url = "/".join(pdf_url.split("/")[:-1])
            
            logging.info(f"[{idx+1}/{len(data_list)}] Đang lấy title mới cho: {article_view_url}")
            
            new_title = get_correct_title(article_view_url)
            
            if new_title and new_title != "N/A":
                logging.info(f" -> Title cũ: {item['title'][:30]}...")
                logging.info(f" -> Title mới: {new_title[:50]}...")
                item['title'] = new_title
                updated_count += 1
            
            # Nghỉ một chút để tránh bị server chặn
            time.sleep(1.0)

    # 3. Ghi đè lại file JSON với title đã sửa
    with open(TARGET_FILE, 'w', encoding='utf-8') as f:
        json.dump(data_list, f, ensure_ascii=False, indent=4)

    logging.info(f"--- HOÀN THÀNH ---")
    logging.info(f"Đã cập nhật thành công {updated_count}/{len(data_list)} bài báo.")

if __name__ == "__main__":
    main()