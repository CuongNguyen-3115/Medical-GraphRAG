import os
import json
import logging
import time
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import google.generativeai as genai

# --- Cấu hình đường dẫn ---
BASE_DIR = r"C:\1. Project\2. DoAn_GraphRAG"
DATA_DIR = os.path.join(BASE_DIR, "Data")
LOG_DIR = os.path.join(BASE_DIR, "logs")
OUTPUT_FILE = os.path.join(DATA_DIR, "(2026_3)_tcnkyh_all_medical_urls.json")

# Tạo thư mục nếu chưa tồn tại
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# --- Khởi tạo Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "(2026_3)_crawl_tcncyh.log"), encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# --- Cấu hình Gemini AI ---
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    logging.error("Không tìm thấy GEMINI_API_KEY trong file .env")
    exit()

genai.configure(api_key=API_KEY)
# Sử dụng gemini-1.5-flash cho tốc độ và hiệu quả phân loại tốt nhất
model = genai.GenerativeModel('gemini-3.1-flash-lite-preview')

def get_domain_from_title(title):
    """Sử dụng Gemini để xác định chuyên khoa y tế từ tiêu đề bài báo"""
    prompt = f"""Bạn là một chuyên gia y tế. Hãy phân loại tiêu đề bài báo sau đây vào một chuyên khoa y học (domain) ngắn gọn (từ 1 đến 3 từ).
    Ví dụ: 'Nội khoa', 'Ung bướu', 'Tim mạch', 'Chẩn đoán hình ảnh'.
    Tiêu đề: {title}
    Trả kết quả chỉ gồm tên chuyên khoa, không giải thích gì thêm."""
    
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logging.error(f"Lỗi khi gọi Gemini cho tiêu đề '{title}': {e}")
        return "Y học chung"

def crawl_article_detail(article_url):
    """Truy cập trang chi tiết bài báo để lấy metadata và link PDF"""
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(article_url, headers=headers, timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 1. Lấy Title từ thẻ <h2>
        title_tag = soup.find('h2') or soup.find('h1', class_='page_title')
        title = title_tag.get_text(strip=True) if title_tag else "N/A"
        
        # 2. Lấy Link PDF từ thẻ <div class="download">
        pdf_url = "N/A"
        download_div = soup.find('div', class_='download')
        if download_div:
            pdf_link_tag = download_div.find('a', class_='pdf')
            if pdf_link_tag:
                pdf_url = pdf_link_tag['href']
        
        # 3. Lấy Published Date
        pub_date = "N/A"
        date_div = soup.find('div', class_='date-published')
        if date_div:
            # Lấy phần text sau nhãn "Đã xuất bản:"
            pub_date = date_div.get_text(strip=True).replace("Đã xuất bản:", "").strip()
            
        # 4. Sử dụng AI để xác định Domain
        domain = get_domain_from_title(title) if title != "N/A" else "N/A"
        
        return {
            "title": title,
            "url": pdf_url,
            "domain": domain,
            "published_date": pub_date,
            "publisher": "Hanoi Medical University Journal",
            "source_type": "scientific_article"
        }
    except Exception as e:
        logging.error(f"Lỗi khi crawl chi tiết tại {article_url}: {e}")
        return None

def main():
    target_url = "https://tapchinghiencuuyhoc.vn/index.php/tcncyh/issue/view/133" #Đổi link này nếu muốn crawl từ số khác của tạp chí (131,132,...)
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    logging.info(f"Bắt đầu crawl danh sách bài báo từ: {target_url}")
    
    try:
        response = requests.get(target_url, headers=headers, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Tìm tất cả các link bài báo trong media-list
        article_summaries = soup.find_all('div', class_='article-summary')
        logging.info(f"Tìm thấy {len(article_summaries)} bài báo tiềm năng.")
        
        results = []
        for idx, summary in enumerate(article_summaries):
            link_tag = summary.find('div', class_='media-body').find('a', href=True)
            if link_tag:
                article_link = link_tag['href']
                logging.info(f"[{idx+1}/{len(article_summaries)}] Đang xử lý: {article_link}")
                
                data = crawl_article_detail(article_link)
                if data:
                    results.append(data)
                
                # Tránh bị chặn và giới hạn API rate limit của Gemini
                time.sleep(1.5)
        
        # Lưu kết quả vào file JSON
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
            
        logging.info(f"Hoàn thành! Đã lưu {len(results)} bản ghi vào {OUTPUT_FILE}")
        
    except Exception as e:
        logging.critical(f"Lỗi nghiêm trọng trong quá trình thực thi: {e}")

if __name__ == "__main__":
    main()