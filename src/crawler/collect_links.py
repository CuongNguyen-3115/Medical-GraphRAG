import requests
from bs4 import BeautifulSoup
import json
import time
import os
import logging
from datetime import datetime

# --- CẤU HÌNH ---
BASE_DIR = r'C:\1. Project\2. DoAn_GraphRAG'
OUT_FILE = os.path.join(BASE_DIR, 'data', 'tim_mach_urls.json')
AJAX_URL = "https://kcb.vn/" # URL gốc để gửi POST kèm Query Params

KEYWORDS = ["tim mạch", "huyết áp", "suy tim", "mạch vành", "động mạch", "tĩnh mạch", "nhồi máu"]

def crawl_medical_v2(total_pages=5):
    all_results = []
    
    # 1. Query String Parameters (Dán vào URL)
    params = {
        'module': 'Content.Listing',
        'moduleId': '12',
        'cmd': 'redraw',
        'site': '2005611',
        'url_mode': 'rewrite',
        'submitFormId': '12',
        'page': 'Article.Download.list'
    }

    # 2. Headers (Giả lập trình duyệt chuẩn)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Referer': 'https://kcb.vn/phac-do',
        'Origin': 'https://kcb.vn'
    }

    for page in range(1, total_pages + 1):
        logging.info(f"Đang xử lý trang {page}...")
        
        # 3. Form Data (Payload POST) - Copy chính xác từ F12 của bạn
        current_ts = int(time.time() * 1000)
        data = {
            'layout': 'Content.Article.Download.listType2',
            'publishTime DESC': '', # Trường đặc biệt trong form của họ
            'type': 'Article.Download',
            'pageNo': page,
            'itemsPerPage': '12',
            'service': 'Content.Article.selectAll',
            'widgetCode': '5b73dd9b9218657408795a12',
            'parentId': '101796520',
            'categoryId': '101796520',
            'widgetTemplateId': '60c959460f89b44851300cf5',
            'page': 'Article.Download.list',
            '_startTime': current_ts - 5000,
            '_t': current_ts
        }

        try:
            # Gửi yêu cầu POST với cả PARAMS (trên URL) và DATA (trong Body)
            response = requests.post(AJAX_URL, params=params, data=data, headers=headers, timeout=20)
            
            if response.status_code == 200 and response.text.strip():
                logging.info(f"Trang {page}: Đã nhận dữ liệu ({len(response.text)} ký tự)")
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Tìm các thẻ chứa link bài viết
                # kcb.vn thường để link trong thẻ <a> có class hoặc cấu trúc cụ thể
                links = soup.find_all('a', href=True)
                found_count = 0
                
                for link in links:
                    title = link.get_text().strip()
                    href = link['href']
                    
                    if "/phac-do/" in href and any(kw in title.lower() for kw in KEYWORDS):
                        full_url = href if href.startswith('http') else f"https://kcb.vn{href}"
                        
                        if not any(item['url'] == full_url for item in all_results):
                            all_results.append({
                                "title": title,
                                "url": full_url,
                                "domain": "Nội tim mạch",
                                "scraped_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            })
                            found_count += 1
                
                logging.info(f"-> Tìm thấy {found_count} tài liệu Tim mạch mới.")
            else:
                logging.warning(f"Trang {page} rỗng hoặc lỗi code: {response.status_code}")

            time.sleep(3) # Nghỉ lâu hơn một chút để an toàn

        except Exception as e:
            logging.error(f"Lỗi trang {page}: {str(e)}")

    # Lưu JSON
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=4)
    logging.info(f"Xong! Tổng cộng lấy được {len(all_results)} link.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    crawl_medical_v2(total_pages=15) # kcb.vn có khá nhiều trang, bạn có thể tăng lên 20-30