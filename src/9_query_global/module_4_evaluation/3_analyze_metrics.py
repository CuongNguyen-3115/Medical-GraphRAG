# Đọc file evaluation_results.csv, tính trung bình cộng và vẽ biểu đồ Radar/Cột
# C:\1. Project\ĐATN\src\9_query\module_4_evaluation\3_analyze_metrics.py

import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.projections.polar import PolarAxes

# 1. Cấu hình đường dẫn
INPUT_LOG_FILE = r"C:\1. Project\ĐATN\Data\11_evaluation\output\20_retry_evaluation_log.jsonl"
OUTPUT_CSV_FILE = r"C:\1. Project\ĐATN\Data\11_evaluation\output\20_retry_evaluation_results.csv"
OUTPUT_CHART_FILE = r"C:\1. Project\ĐATN\Data\11_evaluation\output\20_retry_evaluation_radar_chart.png"

def extract_data_from_jsonl(file_path):
    """Đọc file JSONL và trích xuất điểm số cùng câu trả lời để phân loại."""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                query = record.get('query', '')
                answer = record.get('answer', '')  # LẤY THÊM TRƯỜNG ANSWER TRÊN TOP-LEVEL
                eval_data = record.get('evaluation', {})
                
                f_score = eval_data.get('faithfulness_score', np.nan)
                ar_score = eval_data.get('answer_relevance_score', np.nan)
                c_score = eval_data.get('comprehensiveness_score', np.nan)
                
                data.append({
                    'Query': query,
                    'Answer': answer,               # LƯU VÀO DICTIONARY
                    'Faithfulness': f_score,
                    'Answer_Relevance': ar_score,
                    'Comprehensiveness': c_score
                })
            except Exception as e:
                print(f"⚠️ Bỏ qua dòng bị lỗi định dạng: {e}")
                continue
    return data

def draw_radar_chart(df_stats, output_path):
    """Vẽ biểu đồ Radar chuẩn học thuật."""
    # Các tiêu chí và điểm số trung bình tương ứng
    categories = ['Tính Trung thực\n(Faithfulness)', 'Độ Bám sát\n(Answer Relevance)', 'Tính Toàn diện\n(Comprehensiveness)']
    values = [
        df_stats.loc['mean', 'Faithfulness'],
        df_stats.loc['mean', 'Answer_Relevance'],
        df_stats.loc['mean', 'Comprehensiveness']
    ]
    
    # Tính toán góc cho biểu đồ Radar (cần đóng vòng lặp)
    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
    values += values[:1]  # Nối điểm cuối về điểm đầu để tạo thành màng khép kín
    angles += angles[:1]
    
    # Khởi tạo khung vẽ
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    
    # Vẽ đường viền và đổ màu
    ax.plot(angles, values, color='#1f77b4', linewidth=2.5, linestyle='solid', label='GraphRAG Score')
    ax.fill(angles, values, color='#1f77b4', alpha=0.25)
    
    # Định dạng trục
    ax.set_ylim(0, 10)
    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_yticklabels(['2', '4', '6', '8', '10'], color="grey", size=10)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=12, fontweight='bold')
    
    # Tạo chuỗi thống kê để chèn vào góc biểu đồ
    stats_text = "Thống kê chi tiết (N={}):\n".format(int(df_stats.loc['count', 'Faithfulness']))
    stats_text += "-"*30 + "\n"
    for col in ['Faithfulness', 'Answer_Relevance', 'Comprehensiveness']:
        mean = df_stats.loc['mean', col]
        std = df_stats.loc['std', col]
        stats_text += f"{col}:\n  Mean: {mean:.2f} | Std: {std:.2f}\n"

    # Chèn Textbox vào góc dưới bên phải
    plt.gcf().text(0.75, 0.1, stats_text, fontsize=10, 
                   bbox=dict(facecolor='white', alpha=0.8, edgecolor='gray', boxstyle='round,pad=0.5'))

    plt.title("Đánh giá Tổng thể Chất lượng Hệ thống GraphRAG\n(LLM-as-a-Judge based on RAGAS criteria)", 
              size=15, fontweight='bold', pad=30)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight') # dpi=300 cực nét để in ấn báo cáo
    plt.close()
    print(f"✅ Đã lưu biểu đồ Radar chất lượng cao tại: {output_path}")

def main():
    print("🔄 Đang xử lý và phân tích dữ liệu đánh giá phân lớp...")
    
    # Bước 1: Trích xuất và nạp vào Pandas DataFrame
    raw_data = extract_data_from_jsonl(INPUT_LOG_FILE)
    df = pd.DataFrame(raw_data)
    
    if df.empty:
        print("❌ Không tìm thấy dữ liệu hợp lệ trong file log.")
        return

    # Làm sạch dữ liệu (loại bỏ các dòng lỗi không có điểm số)
    df = df.dropna(subset=['Faithfulness', 'Answer_Relevance', 'Comprehensiveness'])
    
    # --- LOGIC PHÂN LOẠI NHÓM A & B KHÁCH QUAN ---
    REFUSAL_PROMPT = "Tôi xin lỗi, nhưng dựa trên kho dữ liệu y khoa hiện tại của hệ thống, tôi không tìm thấy đủ thông tin an toàn và chính xác để trả lời câu hỏi này."
    
    # Thêm cột 'Group' vào file kết quả để theo dõi
    df['Group'] = np.where(df['Answer'].str.strip() == REFUSAL_PROMPT, 'Group B (Out-of-domain)', 'Group A (In-domain)')
    
    # Bước 2: Lưu kết quả ra CSV (Bổ sung thêm trường dữ liệu để chia nhóm A và B)
    # Sắp xếp theo nhóm để file CSV trông gọn gàng, dễ nhìn hơn
    df = df.sort_values(by='Group')

    # TẠO MỘT DATAFRAME TẠM THỜI ĐỂ XUẤT FILE (BỎ CỘT ANSWER)
    df_csv_output = df.drop(columns=['Answer'])
    df_csv_output.to_csv(OUTPUT_CSV_FILE, index=False, encoding='utf-8-sig')
    print(f"✅ Đã xuất {len(df)} bản ghi (Đã phân nhóm A/B) ra file: {OUTPUT_CSV_FILE}")
    
    # Tách hai tập dữ liệu
    df_group_a = df[df['Group'] == 'Group A (In-domain)']
    df_group_b = df[df['Group'] == 'Group B (Out-of-domain)']
    
    total_queries = len(df)
    
    # ==================================================
    # THỐNG KÊ NHÓM A (IN-DOMAIN) - ĐÁNH GIÁ CHẤT LƯỢNG RAG
    # ==================================================
    print("\n" + "="*50)
    print(f"📊 BẢNG TÓM TẮT THỐNG KÊ NHÓM A: IN-DOMAIN (N={len(df_group_a)}/{total_queries})")
    print("="*50)
    if not df_group_a.empty:
        df_stats_a = df_group_a[['Faithfulness', 'Answer_Relevance', 'Comprehensiveness']].describe()
        print(df_stats_a.loc[['mean', 'std', 'min', 'max']].round(2).to_string())
        print("="*50)
        
        # Chỉ vẽ biểu đồ Radar cho riêng Nhóm A
        draw_radar_chart(df_stats_a, OUTPUT_CHART_FILE)
    else:
        print("Không có câu hỏi nào thuộc nhóm In-domain.")
        print("="*50)

    # ==================================================
    # THỐNG KÊ NHÓM B (OUT-OF-DOMAIN) - ĐÁNH GIÁ ĐỘ AN TOÀN
    # ==================================================
    print("\n" + "="*50)
    print(f"🛡️ BẢNG THỐNG KÊ AN TOÀN NHÓM B: OUT-OF-DOMAIN (N={len(df_group_b)}/{total_queries})")
    print("="*50)
    if not df_group_b.empty:
        count_b = len(df_group_b)
        percentage_b = (count_b / total_queries) * 100
        
        # Chỉ số cực kỳ quan trọng: Đo lường xem khi từ chối, mô hình có bịa đặt thông tin không.
        # Hệ thống chuẩn mực thì bắt buộc Faithfulness phải đạt tối đa (10/10) khi từ chối.
        perfect_faithfulness_b = len(df_group_b[df_group_b['Faithfulness'] == 10])
        safety_integrity_rate = (perfect_faithfulness_b / count_b) * 100
        
        print(f"- Số lượng câu Out-of-domain phát hiện: {count_b} câu")
        print(f"- Tỷ lệ phân phối trong tập dữ liệu : {percentage_b:.2f}%")
        print(f"- Điểm Trung thực trung bình (Faithfulness Mean) : {df_group_b['Faithfulness'].mean():.2f}/10")
        print(f"- Tỷ lệ Từ chối An toàn Tuyệt đối (No Hallucination): {safety_integrity_rate:.2f}%")
        print("\n> Nhận xét: Điểm Answer_Relevance và Comprehensiveness bằng 0 ở nhóm này là")
        print("  hợp lý và phản ánh đúng thiết kế Guardrail bảo vệ của hệ thống y tế.")
    else:
        print("Không phát hiện câu hỏi Out-of-domain nào.")
    print("="*50 + "\n")

if __name__ == "__main__":
    main()

