import json
import os
import re
import pandas as pd

DATA_DIR = r"C:\1. Project\ĐATN\Data\07_Entities_matching"
CLEANED_FILE = os.path.join(DATA_DIR, "2_rule_based_out", "rule_based_mapping.json")
AUDIT_REPORT_CSV = os.path.join(DATA_DIR, "2_rule_based_out", "structural_recovery_audit.csv")

os.makedirs(os.path.dirname(AUDIT_REPORT_CSV), exist_ok=True)

def contains_special_anomalies(text):
    """
    Hàm định lượng phát hiện các ký tự đặc biệt không bình thường/rác trong các thực thể lâm sàng.
    Kỳ vọng 1 thực thể sạch chỉ chứa: Chữ cái, Số, Dấu phẩy, Dấu gạch ngang, Dấu ngoặc tròn, Độ C, %
    """
    if text is None:
        return False
        
    # Phát hiện các ký tự đáng ngờ (Không thuộc bộ ký tự an toàn)
    suspicious_pattern = r"[^\w\s\-,().°+/\'%µ]"
    matches = re.findall(suspicious_pattern, text)
    
    # Phát hiện Entity hoặc Keyword (các chuỗi bị parser gắn nhầm)
    has_parser_garbage = bool(re.search(r"ENTITY|KEYWORD|VALUE|####", text.upper()))
    
    return len(matches) > 0 or has_parser_garbage

def run_quantitative_audit():
    print("⏳ Đang quét lỗi định lượng trên Mapping Log...")
    
    if not os.path.exists(CLEANED_FILE):
        print("❌ LỖI: Không tìm thấy rule_based_mapping.json")
        return
        
    with open(CLEANED_FILE, "r", encoding="utf-8") as f:
        mapping_dict = json.load(f)
        
    audit_records = []
    
    total_original = len(mapping_dict)
    dropped_count = 0
    anomalies_recovered = 0
    anomalies_failed = 0
    clean_passed = 0
    total_anomalies_detected = 0
    
    for original, processed in mapping_dict.items():
        is_original_anomaly = contains_special_anomalies(original)
        
        if is_original_anomaly:
            total_anomalies_detected += 1
            
        if processed is None:
            dropped_count += 1
            if is_original_anomaly:
                audit_records.append({"Original": original, "Processed": "DROPPED", "Status": "SUCCESS_DROP_NOISE"})
            continue
            
        # Kiểm tra nếu processed là list
        processed_list = processed if isinstance(processed, list) else [processed]
        
        for proc in processed_list:
            is_processed_anomaly = contains_special_anomalies(proc)
            
            if is_original_anomaly and not is_processed_anomaly:
                anomalies_recovered += 1
                audit_records.append({"Original": original, "Processed": proc, "Status": "SUCCESS_RECOVERY"})
            elif is_processed_anomaly:
                anomalies_failed += 1
                audit_records.append({"Original": original, "Processed": proc, "Status": "FAILED_LEAK"})
            elif not is_original_anomaly and not is_processed_anomaly:
                clean_passed += 1

    df_audit = pd.DataFrame(audit_records)
    if not df_audit.empty:
        # Sắp xếp các FAILED_LEAK lên đầu để dễ kiểm tra
        df_audit = df_audit.sort_values(by="Status", ascending=True)
        df_audit.to_csv(AUDIT_REPORT_CSV, index=False, encoding="utf-8-sig")
        
    recovery_rate = (anomalies_recovered / total_anomalies_detected) * 100 if total_anomalies_detected > 0 else 0
    drop_rate = (len([r for r in audit_records if r["Status"]=="SUCCESS_DROP_NOISE"]) / total_anomalies_detected) * 100 if total_anomalies_detected > 0 else 0
    
    print("\n" + "="*50)
    print("📊 BÁO CÁO KIỂM TOÁN CẤU TRÚC ĐỊNH LƯỢNG (PHASE 2 - RULE-BASED)")
    print("="*50)
    print(f"🔹 Tổng số thực thể ánh xạ (Mapping Keys): {total_original:,}")
    print(f"🔹 Số thực thể sạch đi qua an toàn: {clean_passed:,}")
    print(f"🔹 Tổng số thực thể dị thường phát hiện ở đầu vào: {total_anomalies_detected:,}")
    print(f"✅ Số dị thường được CỨU & KHÔI PHỤC cấu trúc: {anomalies_recovered:,} ({recovery_rate:.2f}%)")
    print(f"🗑️ Số lượng rác cấu trúc được LOẠI BỎ (DROP): {dropped_count:,}")
    
    print(f"🚨 Dị thường bị LỌT LƯỚI (Failed Leak - Lỗi chưa được fix sạch): {anomalies_failed:,}")
    
    if anomalies_failed > 0:
        print(f"\n⚠️ CẢNH BÁO: Còn {anomalies_failed} thực thể lọt lưới (Leakage).")
        print(f"   Ví dụ: Parser chèn các ký tự đặc biệt ở giữa chuỗi, không chỉ ở đầu chuỗi.")
        print(f"   Vui lòng kiểm tra file {AUDIT_REPORT_CSV} để cập nhật 2a_rule_based_normalization.py!")
    else:
        print("\n✅ TUYỆT VỜI: Không có thực thể lọt lưới (Leak = 0). Cấu trúc dữ liệu đã sẵn sàng cho Phase 3!")

if __name__ == "__main__":
    run_quantitative_audit()

