import json
from pathlib import Path
from collections import defaultdict
import statistics

# Cấu hình đường dẫn
BASE_DIR = Path(r"C:\1. Project\ĐATN")
DATA_DIR = BASE_DIR / "Data"
FILTERED_COMMUNITIES_PATH = DATA_DIR / "08_Communities_detecting" / "filtered_communities.json"

def analyze_communities(file_path: Path = FILTERED_COMMUNITIES_PATH):
    """
    Phân tích và thống kê các chỉ số chất lượng từ đồ thị/cộng đồng 
    đã được lọc để đánh giá chất lượng phân cụm.
    """
    print(f"[*] Đang đọc dữ liệu từ: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            communities = json.load(f)
    except FileNotFoundError:
        print(f"[!] Lỗi: Không tìm thấy file {file_path}")
        return
    except json.JSONDecodeError:
        print(f"[!] Lỗi: File {file_path} không đúng định dạng JSON")
        return

    total_communities = len(communities)
    
    print("\n" + "="*50)
    print("   BÁO CÁO THỐNG KÊ CHẤT LƯỢNG CỘNG ĐỒNG")
    print("="*50)
    print(f"Tổng số cộng đồng: {total_communities}")

    if total_communities == 0:
        print("Không có từ liệu cộng đồng để thống kê.")
        return

    level_dist = defaultdict(int)
    node_counts = []
    edge_counts = []
    all_unique_nodes = set()

    for comm in communities:
        # Thống kê theo level
        level = comm.get("level", -1)
        level_dist[level] += 1
        
        # Thống kê Node
        nodes = comm.get("nodes", [])
        node_counts.append(len(nodes))
        
        for node in nodes:
            # Xử lý tùy thuộc vào cấu trúc dữ liệu của node (dict hoặc chuỗi id)
            if isinstance(node, dict):
                node_id = node.get("id", str(node))
            else:
                node_id = str(node)
            all_unique_nodes.add(node_id)

        # Thống kê Edge (nếu có trường edges)
        edges = comm.get("edges", [])
        if edges:
            edge_counts.append(len(edges))

    # In kết quả phân bố Level
    print("\n1. Phân bố cộng đồng theo Level (Độ sâu phân cấp):")
    for lvl in sorted(level_dist.keys()):
        label = f"Level {lvl}" if lvl != -1 else "Không xác định Level"
        print(f"   - {label}: {level_dist[lvl]} cộng đồng")

    # In kết quả Thống kê Node
    print(f"\n2. Thống kê Node (Thực thể):")
    print(f"   - Tổng số unique nodes (ước tính): {len(all_unique_nodes)}")
    print(f"   - Kích thước cộng đồng lớn nhất: {max(node_counts)} nodes")
    print(f"   - Kích thước cộng đồng nhỏ nhất: {min(node_counts)} nodes")
    print(f"   - Kích thước trung bình / cộng đồng: {statistics.mean(node_counts):.2f} nodes")
    
    if total_communities >= 2:
        print(f"   - Độ lệch chuẩn (Standard Deviation): {statistics.stdev(node_counts):.2f}")
        print(f"   - Trung vị (Median): {statistics.median(node_counts):.2f} nodes")

    # In kết quả Thống kê Cạnh
    print(f"\n3. Thống kê Edge (Quan hệ/Cạnh):")
    if edge_counts:
        print(f"   (Dữ liệu từ {len(edge_counts)} cộng đồng có chứa thông tin 'edges')")
        print(f"   - Số cạnh nhiều nhất trong 1 cộng đồng: {max(edge_counts)}")
        print(f"   - Số cạnh ít nhất trong 1 cộng đồng: {min(edge_counts)}")
        print(f"   - Số cạnh trung bình / cộng đồng: {statistics.mean(edge_counts):.2f}")
    else:
        print("   - Không tìm thấy dữ liệu 'edges' trực tiếp trong dictionary của cộng đồng này.")

    print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    analyze_communities()
