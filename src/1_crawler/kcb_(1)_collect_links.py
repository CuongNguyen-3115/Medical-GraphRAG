import requests
from bs4 import BeautifulSoup
import json
import time
import os
import logging
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv

# --- 1. CẤU HÌNH MÔI TRƯỜNG & AI ---
load_dotenv() # Tự động tìm file .env ở thư mục gốc
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("Không tìm thấy GEMINI_API_KEY trong file .env")

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-3.1-flash-lite-preview') # Dùng bản Flash để tốc độ nhanh và tiết kiệm

# --- 2. CẤU HÌNH ĐƯỜNG DẪN ---
BASE_DIR = r'C:\1. Project\2. DoAn_GraphRAG'
OUT_FILE = os.path.join(BASE_DIR, 'data', 'kcb_all_medical_urls.json')
AJAX_URL = "https://kcb.vn/"

# --- 3. HÀM PHÂN LOẠI BẰNG LLM ---
def classify_medical_domain(title):
    """Cải tiến Prompt để hạn chế 'Chuyên khoa khác'"""
    prompt = f"""
    Bạn là một chuyên gia phân loại tài liệu y tế chuyên sâu. 
    Dựa trên tiêu đề: "{title}"
    Hãy xác định chuyên khoa chính xác nhất (ví dụ: Răng Hàm Mặt, Kiểm soát nhiễm khuẩn, Ung bướu, Ngoại khoa, Da liễu, v.v.).
    Nếu tiêu đề quá chung chung không thuộc chuyên khoa nào, hãy trả về 'Y tế công cộng'.
    Chỉ trả về tên chuyên khoa, không giải thích.
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return "Chưa phân loại"

# --- 4. HÀM CRAWLER CHÍNH ---
def crawl_all_medical_data(total_pages=5):
    all_results = []
    
    params = {
        'module': 'Content.Listing', 'moduleId': '12', 'cmd': 'redraw',
        'site': '2005611', 'url_mode': 'rewrite', 'submitFormId': '12',
        'page': 'Article.Download.list'
    }

    headers = {
        'User-Agent': 'Mozilla/5.0...',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://kcb.vn/phac-do'
    }

    logging.info(f"Bắt đầu cào toàn bộ dữ liệu ({total_pages} trang)...")

    for page in range(1, total_pages + 1):
        logging.info(f"--- Đang xử lý trang {page} ---")
        
        data = {
            'layout': 'Content.Article.Download.listType2',
            'type': 'Article.Download',
            'pageNo': page,
            'itemsPerPage': '12',
            'service': 'Content.Article.selectAll',
            'widgetCode': '5b73dd9b9218657408795a12',
            'parentId': '101796520',
            'categoryId': '101796520',
            'page': 'Article.Download.list',
            '_startTime': int(time.time() * 1000) - 5000,
            '_t': int(time.time() * 1000)
        }

        try:
            response = requests.post(AJAX_URL, params=params, data=data, headers=headers, timeout=60)
            
            if response.status_code == 200 and response.text.strip():
                soup = BeautifulSoup(response.text, 'html.parser')
                links = soup.find_all('a', href=True)
                
                for link in links:
                    title = link.get_text().strip()
                    href = link['href']
                    
                    # Chỉ lấy các link thuộc chuyên mục phác đồ
                    if "/phac-do/" in href and title:
                        full_url = href if href.startswith('http') else f"https://kcb.vn{href}"
                        
                        # Kiểm tra trùng URL
                        if not any(item['url'] == full_url for item in all_results):
                            # GỌI LLM ĐỂ PHÂN LOẠI
                            logging.info(f"Đang phân loại: {title[:50]}...")
                            domain = classify_medical_domain(title)
                            
                            all_results.append({
                                "title": title,
                                "url": full_url,
                                "domain": domain,
                                "scraped_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            })
                            # Nghỉ ngắn giữa các lần gọi AI để tránh dính Rate Limit (nếu dùng Free Tier)
                            time.sleep(1) 
            
            time.sleep(2) # Nghỉ giữa các trang web

        except Exception as e:
            logging.error(f"Lỗi tại trang {page}: {str(e)}")

    # Lưu toàn bộ vào file JSON
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=4)
    
    logging.info(f"HOÀN THÀNH! Đã lưu {len(all_results)} tài liệu vào {OUT_FILE}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    crawl_all_medical_data(total_pages=5) # Bạn có thể tăng lên để vét toàn bộ trang web