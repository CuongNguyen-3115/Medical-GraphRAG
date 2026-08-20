# C:\1. Project\ĐATN\src\9_query\module_4_evaluation\utils\filter_failed_queries.py

import os
import pandas as pd
import json
import logging

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

# --- CẤU HÌNH ĐƯỜNG DẪN ---
# Đường dẫn file CSV kết quả đánh giá (Đầu vào)
INPUT_CSV_PATH = r"C:\1. Project\ĐATN\Data\11_evaluation\output\evaluation_results.csv"

# Thư mục và file JSONL để lưu các query cần chạy lại (Đầu ra)
OUTPUT_DIR = r"C:\1. Project\ĐATN\Data\10_query\retry_queries"
OUTPUT_FILE_PATH = os.path.join(OUTPUT_DIR, "failed_queries_retry.jsonl")

def filter_and_save_failed_queries():
    # Kiểm tra xem file CSV có tồn tại không
    if not os.path.exists(INPUT_CSV_PATH):
        logging.error(f"Không tìm thấy file CSV tại: {INPUT_CSV_PATH}")
        return

    try:
        # 1. Đọc dữ liệu từ CSV (Pandas sẽ tự động xử lý triệt để các dấu ngoặc kép)
        logging.info("Đang đọc dữ liệu từ file CSV...")
        df = pd.read_csv(INPUT_CSV_PATH, encoding='utf-8')
        
        # Kiểm tra xem các cột cần thiết có tồn tại không
        required_columns = ['Query', 'Faithfulness', 'Answer_Relevance', 'Comprehensiveness']
        for col in required_columns:
            if col not in df.columns:
                logging.error(f"File CSV thiếu cột quan trọng: '{col}'")
                return

        # 2. Lọc các dòng có 1 trong 3 tiêu chí bằng 0
        logging.info("Đang lọc các query có điểm 0...")
        condition = (df['Faithfulness'] == 0) | (df['Answer_Relevance'] == 0) | (df['Comprehensiveness'] == 0)
        failed_df = df[condition]
        
        # 3. Trích xuất danh sách các câu hỏi
        # Lấy cột 'Query', loại bỏ khoảng trắng thừa ở 2 đầu (strip), và chuyển thành dạng list
        failed_queries = failed_df['Query'].str.strip().tolist()
        
        logging.info(f"Tìm thấy {len(failed_queries)} queries cần chạy lại.")

        if len(failed_queries) == 0:
            logging.info("Không có query nào cần phải chạy lại. Chúc mừng!")
            return

        # 4. Đảm bảo thư mục đầu ra tồn tại
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # 5. Ghi ra file .jsonl với định dạng {"question": "nội dung query"}
        logging.info(f"Đang lưu kết quả ra file: {OUTPUT_FILE_PATH}")
        with open(OUTPUT_FILE_PATH, 'w', encoding='utf-8') as f:
            for query in failed_queries:
                # Tạo dictionary đúng cấu trúc
                json_record = {"question": query}
                # Ghi từng dòng json
                f.write(json.dumps(json_record, ensure_ascii=False) + '\n')
                
        logging.info("✅ Hoàn tất việc tạo file danh sách query chạy lại!")

    except Exception as e:
        logging.error(f"Đã xảy ra lỗi trong quá trình xử lý: {e}")

if __name__ == "__main__":
    filter_and_save_failed_queries()