import json
import requests
from bs4 import BeautifulSoup
import re

def extract_published_date(url):
    try:
        # Giả lập trình duyệt để tránh bị chặn
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 1. Tìm thẻ cha chứa ngày đăng
            date_container = soup.find('span', class_='article-date')
            
            if date_container:
                # 2. Tìm thẻ con chứa giá trị ngày (thẻ span class="mau")
                date_element = date_container.find('span', class_='mau')
                
                if date_element:
                    time_text = date_element.get_text(strip=True)
                    
                    # 3. Dùng Regex để trích xuất chuẩn dd/mm/yyyy từ chuỗi
                    date_match = re.search(r'(\d{2}/\d{2}/\d{4})', time_text)
                    if date_match:
                        return date_match.group(1)
            
            # Trường hợp dự phòng nếu cấu trúc trên không tìm thấy, thử tìm trực tiếp class "mau"
            backup_element = soup.find('span', class_='mau')
            if backup_element:
                date_match = re.search(r'(\d{2}/\d{2}/\d{4})', backup_element.get_text())
                if date_match:
                    return date_match.group(1)

        return "Unknown"
    except Exception as e:
        print(f"Lỗi khi truy cập {url}: {e}")
        return "Error"

# Đường dẫn file của bạn
file_path = r'C:\1. Project\2. DoAn_GraphRAG\Data\all_medical_urls.json'

# Đọc file JSON hiện tại
try:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Duyệt qua từng mục và bổ sung trường Date
    for item in data:
        if 'url' in item:
            # Chỉ cào nếu chưa có ngày hoặc ngày đang là Unknown/Error (để tiết kiệm thời gian)
            if item.get('Published_Date') in [None, "Unknown", "Error"]:
                print(f"Đang trích xuất ngày cho: {item['url']}")
                item['Published_Date'] = extract_published_date(item['url'])

    # Lưu lại file JSON đã cập nhật
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print("--- Hoàn thành cập nhật metadata thời gian! ---")

except FileNotFoundError:
    print(f"Lỗi: Không tìm thấy file tại đường dẫn {file_path}")
except Exception as e:
    print(f"Đã xảy ra lỗi hệ thống: {e}")