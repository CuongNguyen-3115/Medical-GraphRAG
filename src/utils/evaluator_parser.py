import re
import fitz # PyMuPDF

def evaluate_cleaning_quality(text):
    """Đánh giá chất lượng nội dung Markdown sau khi convert."""
    if not text: return 0, {}
    
    metrics = {}
    # 1. Garbage ratio: Ký tự không phải chữ/số/dấu câu/tiếng Việt
    text_no_space = re.sub(r'\s', '', text)
    valid_chars = re.findall(r'[\w\d.,!?;:()\-#|*àáảãạâầấẩẫậăằắẳẵặèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵĐđ]', text_no_space)
    metrics['garbage_ratio'] = 1 - (len(valid_chars) / len(text_no_space)) if text_no_space else 1
    
    # 2. Markdown Table check: Kiểm tra xem có cấu trúc bảng |---| không
    metrics['has_tables'] = bool(re.search(r'\|.*\|', text))
    
    score = 100 * (1 - metrics['garbage_ratio'])
    return max(0, score), metrics

def estimate_info_loss(pdf_path, md_text):
    """So sánh số lượng bảng/ảnh trong PDF gốc với nội dung Markdown."""
    doc = fitz.open(pdf_path)
    num_images = 0
    num_tables = 0
    
    for page in doc:
        num_images += len(page.get_images(full=True))
        tabs = page.find_tables()
        num_tables += len(tabs.tables)
    
    # Kiểm tra sơ bộ sự hiện diện trong MD
    md_table_count = len(re.findall(r'\|--+', md_text)) # Đếm các dòng kẻ bảng
    
    loss_metrics = {
        "original_images": num_images,
        "original_tables": num_tables,
        "detected_md_tables": md_table_count,
        "info_loss_level": "High" if (num_tables > 0 and md_table_count == 0) else "Low"
    }
    return loss_metrics