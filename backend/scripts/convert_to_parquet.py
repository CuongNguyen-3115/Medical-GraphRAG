# Vị trí: backend/scripts/convert_to_parquet.py
import duckdb
import os

def convert():
    # Xác định đường dẫn tương đối từ script tới thư mục data
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    jsonl_path = os.path.join(base_dir, 'data', 'summaries_final.jsonl')
    parquet_path = os.path.join(base_dir, 'data', 'summaries_final.parquet')

    print(f"Đang đọc dữ liệu từ: {jsonl_path}")
    
    # DuckDB tự động nội suy cấu trúc và ghi ra Parquet
    query = f"""
        COPY (
            SELECT * FROM read_json_auto('{jsonl_path}')
        ) 
        TO '{parquet_path}' (FORMAT PARQUET);
    """
    duckdb.sql(query)
    print(f"✅ Đã lưu thành công Parquet tại: {parquet_path}")

if __name__ == "__main__":
    convert()