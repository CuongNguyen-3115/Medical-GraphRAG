import json
import os
import re

# ĐƯỜNG DẪN ĐẾN FILE BÁO CÁO MAPPING CỦA BẠN
DATA_DIR = r"C:\1. Project\ĐATN\Data\07_Entities_matching"
MAPPING_FILE = os.path.join(DATA_DIR, "3_fuzzy_out", "fuzzy_mapping_report.json")
LOG_VIOLATION_FILE = os.path.join(DATA_DIR, "3_fuzzy_out", "validation_violations.json")

def extract_critical_identifiers(text):
    """Hàm trích xuất định danh cốt lõi (B, C, D, số liều lượng...)"""
    numbers = re.findall(r'\d+', text.upper())
    letters = re.findall(r'\b[A-Z]\b', text.upper())
    romans = re.findall(r'\b(?:I{1,4}|IV|V|VI{1,3}|IX|X{1,3}|IVS)\b', text.upper())
    critical_vocab = 'NÃO|NẤM|THỊ|VỊ|KHỨU|THÍNH|XÚC|TRÁI|PHẢI|TRÊN|DƯỚI|TRONG|NGOÀI|TRƯỚC|SAU|TĨNH|ĐỘNG|CẤP|MẠN|ÂM|DƯƠNG|LÀNH|ÁC|TIM|GAN|PHỔI|THẬN|MẬT|MÁU|MỦ|MẮT|MŨI|MIỆNG|TAI|CỔ|HỌNG|NGỰC|BỤNG|LƯNG|TAY|CHÂN|DA|CƠ|MỠ|XƯƠNG|KHỚP'
    vocabs = re.findall(fr'\b(?:{critical_vocab})\b', text.upper())
    return set(numbers + letters + romans + vocabs)

def validate_mapping():
    if not os.path.exists(MAPPING_FILE):
        print(f"❌ Không tìm thấy file cần kiểm định tại: {MAPPING_FILE}")
        return

    with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
        mapping_data = json.load(f)

    total_checks = len(mapping_data)
    violations = {}
    correct_merges = 0
    self_mappings = 0

    print(f"⏳ Đang tiến hành kiểm định tự động {total_checks:,} cặp mapping...")

    for original, canonical in mapping_data.items():
        # Nếu từ gốc trùng từ chuẩn (không gộp gì cả), bỏ qua check
        if original == canonical:
            self_mappings += 1
            continue

        ids_original = extract_critical_identifiers(original)
        ids_canonical = extract_critical_identifiers(canonical)

        # KIỂM TRA ĐỊNH LƯỢNG: Nếu có định danh và định danh KHÁC nhau -> LỖI
        if ids_original and ids_canonical:
            if ids_original != ids_canonical:
                violations[original] = {
                    "mapped_to": canonical,
                    "original_identifiers": list(ids_original),
                    "canonical_identifiers": list(ids_canonical)
                }
                continue
        
        correct_merges += 1

    # --- XUẤT BÁO CÁO ĐỊNH LƯỢNG KẾT QUẢ ---
    print("\n📊 ==================== KẾT QUẢ KIỂM ĐỊNH MAPPING ====================")
    print(f"🔹 Tổng số cặp thực thể được quét: {total_checks:,}")
    print(f"🔹 Số Node giữ nguyên không gộp: {self_mappings:,}")
    print(f"🔹 Số cặp gộp đúng chuẩn định danh: {correct_merges:,}")
    print(f"❌ Số trường hợp phát hiện GOM NHẦM (Violations): {len(violations)}")
    
    # Tính toán chỉ số an toàn dữ liệu (Data Safety Score)
    gộp_sai_rate = (len(violations) / (correct_merges + len(violations))) * 100 if (correct_merges + len(violations)) > 0 else 0
    precision_score = 100 - gộp_sai_rate
    print(f"🎯 Độ chính xác định danh (Identifier Precision Score): {precision_score:.2f}%")
    print("====================================================================")

    if violations:
        print(f"⚠️ CẢNH BÁO: Phát hiện lỗi! Chi tiết lỗi đã được ghi vào: {LOG_VIOLATION_FILE}")
        with open(LOG_VIOLATION_FILE, 'w', encoding='utf-8') as f:
            json.dump(violations, f, ensure_ascii=False, indent=4)
        print("🛑 Trạng thái kiểm định: FAILED. Vui lòng kiểm tra lại hàm chặn mã tử.")
    else:
        print("🎉 Trạng thái kiểm định: PASSED! File mapping đạt độ an toàn tuyệt đối 100%.")
        if os.path.exists(LOG_VIOLATION_FILE):
            os.remove(LOG_VIOLATION_FILE) # Xóa file log cũ nếu đã sạch lỗi

if __name__ == "__main__":
    validate_mapping()