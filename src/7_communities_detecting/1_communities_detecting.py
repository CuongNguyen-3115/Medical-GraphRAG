import json
import os
import logging
from datetime import datetime
import igraph as ig
import leidenalg
import math  
from collections import Counter

# ================= CẤU HÌNH ĐƯỜNG DẪN =================
BASE_DIR = r"C:\1. Project\ĐATN"
DATA_DIR = os.path.join(BASE_DIR, "Data")
INPUT_NODES_PATH = os.path.join(DATA_DIR, "07_Entities_matching", "6_graph_final", "nodes.json")
INPUT_EDGES_PATH = os.path.join(DATA_DIR, "07_Entities_matching", "6_graph_final", "edges.json")

OUTPUT_DIR = os.path.join(DATA_DIR, "08_Communities_detecting")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "communities.json")

LOG_DIR = os.path.join(BASE_DIR, "logs", "08_communities_detecting")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# ================= CẤU HÌNH LOGGING =================
log_filename = os.path.join(LOG_DIR, f"leiden_detect_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def main():
    logging.info("--- BẮT ĐẦU QUÁ TRÌNH PHÁT HIỆN CỘNG ĐỒNG (LEIDEN ALGORITHM) ---")
    
    # 1. Load Data
    logging.info(f"Đang đọc dữ liệu từ: {INPUT_NODES_PATH}")
    nodes_data = load_json(INPUT_NODES_PATH)
    logging.info(f"Đang đọc dữ liệu từ: {INPUT_EDGES_PATH}")
    edges_data = load_json(INPUT_EDGES_PATH)
    
    logging.info(f"Tổng số Nodes ban đầu: {len(nodes_data)}")
    logging.info(f"Tổng số Edges ban đầu: {len(edges_data)}")

    # 2. Tiền xử lý dữ liệu và Self-healing
    logging.info("Đang kiểm tra tính toàn vẹn và chạy Self-healing...")
    
    node_names = [node["entity_name"] for node in nodes_data]
    name_to_id = {name: i for i, name in enumerate(node_names)}
    
    edges_list = []
    weights = []
    valid_edges_data = []
    auto_created_count = 0

    for edge in edges_data:
        source = edge.get("source")
        target = edge.get("target")
        
        if not source or not target: continue
        
        # --- SELF HEALING CHO SOURCE ---
        if source not in name_to_id:
            new_node = {
                "entity_name": source,
                "entity_types": ["UNKNOWN"], # Gán type mặc định
                "descriptions": ["Auto-generated from Relationship"],
                "source_chunks": edge.get("source_chunks", []), # Thừa kế source_chunk từ edge
                "occurrence_count": 1
            }
            nodes_data.append(new_node)
            node_names.append(source)
            name_to_id[source] = len(nodes_data) - 1
            auto_created_count += 1
            logging.info(f"[Self-healing] Tạo Node mới: {source}")

        # --- SELF HEALING CHO TARGET ---
        if target not in name_to_id:
            new_node = {
                "entity_name": target,
                "entity_types": ["UNKNOWN"],
                "descriptions": ["Auto-generated from Relationship"],
                "source_chunks": edge.get("source_chunks", []),
                "occurrence_count": 1
            }
            nodes_data.append(new_node)
            node_names.append(target)
            name_to_id[target] = len(nodes_data) - 1
            auto_created_count += 1
            logging.info(f"[Self-healing] Tạo Node mới: {target}")

        # Chèn Edge (Lúc này chắc chắn 100% source và target đều hợp lệ)
        edges_list.append((name_to_id[source], name_to_id[target]))
        weights.append(edge.get("weight", 1.0))
        valid_edges_data.append(edge)

    logging.info(f"Tổng số Node tự động tạo thêm: {auto_created_count}")
    logging.info(f"Tổng số Nodes sau Self-healing: {len(nodes_data)}")

    # 3. Xây dựng đồ thị bằng igraph
    logging.info("Khởi tạo đồ thị igraph...")
    g = ig.Graph(directed=False)
    
    # Khởi tạo vertices và gắn attributes
    g.add_vertices(len(nodes_data))
    g.vs["name"] = node_names
    g.vs["attributes"] = nodes_data

    # Add edges và weights
    g.add_edges(edges_list)
    g.es["weight"] = weights
    g.es["attributes"] = valid_edges_data
    
    logging.info(f"Đồ thị đã xây dựng: {g.vcount()} đỉnh, {g.ecount()} cạnh.")

    # ================= ĐOẠN SCRIPT PHÂN TÍCH KẾT NỐI VĨ MÔ =================
    logging.info("--- KHẢO SÁT SỰ PHÂN MẢNH ĐỒ THỊ (CONNECTED COMPONENTS) ---")
    
    # 1. Tìm tất cả các thành phần liên thông (Weakly Connected Components)
    components = g.connected_components(mode='weak')
    num_components = len(components)
    logging.info(f"[Định lượng] Tổng số 'Hòn đảo tri thức' độc lập: {num_components}")
    
    if num_components > 0:
        component_sizes = components.sizes()
        
        # 2. Tìm Lục địa tri thức (Giant Component)
        giant_size = max(component_sizes)
        giant_pct = (giant_size / g.vcount()) * 100
        logging.info(f"[Định lượng] Kích thước Hòn đảo lớn nhất (Giant Component): {giant_size} nodes ({giant_pct:.2f}% toàn bộ đồ thị)")
        
        # 3. Phân tích các hòn đảo mồ côi/vụn vặt
        size_counts = Counter(component_sizes)
        tiny_islands_count = sum(count for size, count in size_counts.items() if size <= 3)
        isolated_nodes_count = size_counts.get(1, 0)
        isolated_pairs_count = size_counts.get(2, 0)
        
        logging.info(f"[Phân tích] Số hòn đảo siêu nhỏ (<= 3 nodes): {tiny_islands_count}")
        logging.info(f"[Chi tiết] Số node hoàn toàn cô lập (Size=1): {isolated_nodes_count}")
        logging.info(f"[Chi tiết] Số cặp node chỉ nối với nhau (Size=2): {isolated_pairs_count}")
        
        # Top 5 kích thước phổ biến nhất để xem xu hướng phân mảnh
        top_sizes = size_counts.most_common(5)
        logging.info(f"[Chi tiết] Top 5 kích thước cụm phổ biến nhất (Size: Số lượng cụm): {top_sizes}")
        
        # 4. Xác thực giới hạn thuật toán
        if num_components > 1000:
            logging.warning(f"CẢNH BÁO: Đồ thị bị phân mảnh thành {num_components} mảnh độc lập. Thuật toán Leiden sẽ KHÔNG THỂ gộp số lượng cộng đồng xuống thấp hơn con số này dù Max Levels cao đến đâu!")
            
    logging.info("---------------------------------------------------------------")
    # ================= KẾT THÚC ĐOẠN SCRIPT PHÂN TÍCH =================
    
    # ================= ĐOẠN SCRIPT CẮT TỈA (PRUNING) ĐỒ THỊ =================
    logging.info("--- BẮT ĐẦU CẮT TỈA (PRUNING) ĐỒ THỊ ---")
    
    # 1. Xác định kích thước của từng thành phần liên thông
    components = g.connected_components(mode='weak')
    
    # 2. Lọc danh sách các node thuộc về các cụm hợp lệ (Size >= 3)
    # Bạn có thể điều chỉnh số 3 thành 2 hoặc 4 tùy độ khắt khe
    valid_node_indices = [
        v for v in range(g.vcount()) 
        if len(components[components.membership[v]]) >= 3
    ]
    
    nodes_before = g.vcount()
    
    # 3. Tạo đồ thị con (subgraph) chỉ chứa các node hợp lệ
    g = g.subgraph(valid_node_indices)
    
    nodes_after = g.vcount()
    logging.info(f"[Pruning] Đã xóa {nodes_before - nodes_after} nodes thuộc các hòn đảo vụn vặt (Size < 3).")
    logging.info(f"[Pruning] Kích thước đồ thị sau cắt tỉa: {g.vcount()} đỉnh, {g.ecount()} cạnh.")
    logging.info("---------------------------------------------------------------")
    # ========================================================================

    # ================= BẮT ĐẦU ĐOẠN CODE CẦN BỔ SUNG =================
    logging.info("Đang tính toán Degree cho Nodes và Priority Score cho Edges...")
    
    # Tính tổng trọng số các cạnh kết nối với mỗi node (Weighted Degree)
    node_degrees = g.strength(weights="weight")
    
    # Cập nhật trường 'degree' vào thuộc tính của từng Node
    for i, node_attr in enumerate(g.vs["attributes"]):
        node_attr["degree"] = node_degrees[i]

    # Cập nhật trường 'priority_score' vào thuộc tính của từng Edge
    for i, edge_attr in enumerate(g.es["attributes"]):
        source_idx, target_idx = g.es[i].tuple
        # Priority Score = Degree của Source + Degree của Target
        edge_attr["priority_score"] = node_degrees[source_idx] + node_degrees[target_idx]
    # ================= KẾT THÚC ĐOẠN CODE CẦN BỔ SUNG =================

    current_graph = g.copy()
    current_level = 0
    max_levels = 5  # Giới hạn số cấp độ (tránh lặp vô hạn nếu đồ thị quá lớn)
    final_communities = []
    global_comm_id = 0  # Bộ đếm ID duy nhất cho tất cả các cộng đồng
    current_resolution = 1.0

    # Mapping: Lưu vết ID của original_node thuộc về node nào trong đồ thị hiện tại
    # Ban đầu (trước Level 0), mỗi original_node tương ứng với chính nó
    node_to_prev_comm = {i: i for i in range(g.vcount())}
    
    # Lưu vết community_id của các siêu nút ở level trước
    prev_level_comm_ids = []

    while current_level < max_levels:
        logging.info(f"--- BẮT ĐẦU PHÂN CỤM LEVEL {current_level} ---")
        
        # Điều kiện dừng 1: Đồ thị đã bị gập thành 1 Siêu nút duy nhất
        if current_graph.vcount() <= 1:
            logging.info("Đồ thị đã gộp thành 1 cộng đồng duy nhất. Dừng phân cấp.")
            break

        # Chạy Leiden trên đồ thị của cấp độ hiện tại
        partition = leidenalg.find_partition(
            current_graph, 
            leidenalg.CPMVertexPartition, # Đổi sang CPM
            weights=current_graph.es["weight"],
            resolution_parameter=current_resolution, 
            n_iterations=-1,
            seed=42 # Fix seed để đảm bảo kết quả phân cụm không thay đổi
        )
        
        num_communities = len(partition)
        logging.info(f"Level {current_level}: Phát hiện {num_communities} communities. Modularity: {partition.quality():.4f}")

        # Điều kiện dừng 2: Thuật toán không thể gộp thêm (Số cộng đồng = Số nút hiện tại)
        if num_communities == current_graph.vcount():
            logging.info("Thuật toán không thể tối ưu thêm (không có sự gộp node). Dừng phân cấp.")
            break

        # Cập nhật Mapping: Xác định original_node thuộc về cộng đồng nào ở Level HIỆN TẠI
        node_to_curr_comm = {}
        for orig_idx, prev_comm_idx in node_to_prev_comm.items():
            curr_comm_idx = partition.membership[prev_comm_idx]
            node_to_curr_comm[orig_idx] = curr_comm_idx

        # Khởi tạo cấu trúc lưu trữ cho các cộng đồng ở Level hiện tại
        level_communities = {}
        for i in range(num_communities):
            level_communities[i] = {
                "community_id": global_comm_id, # ID dạng số nguyên duy nhất
                "level": current_level,
                "nodes": [],
                "edges": [],
                "sub_communities": []
            }
            global_comm_id += 1

        # Cập nhật sub_communities (từ level > 0, các node thực chất là super node của level trước)
        if current_level > 0:
            for super_node_idx, curr_comm_idx in enumerate(partition.membership):
                prev_comm_id = prev_level_comm_ids[super_node_idx]
                level_communities[curr_comm_idx]["sub_communities"].append(prev_comm_id)

        # Gom Nodes (Duyệt qua đồ thị GỐC 'g' để lấy data nguyên bản)
        for orig_idx, curr_comm_idx in node_to_curr_comm.items():
            level_communities[curr_comm_idx]["nodes"].append(g.vs[orig_idx]["attributes"])

        # Gom Edges (Duyệt qua đồ thị GỐC 'g')
        for edge in g.es:
            source_idx, target_idx = edge.tuple
            comm_source = node_to_curr_comm[source_idx]
            comm_target = node_to_curr_comm[target_idx]
            
            # Nếu 2 node của cạnh gốc rơi vào CÙNG 1 cộng đồng ở level này -> Cạnh đó thuộc về cộng đồng
            if comm_source == comm_target:
                level_communities[comm_source]["edges"].append(edge["attributes"])

        # Lọc bỏ các cộng đồng rỗng (nếu có) và đưa vào kết quả cuối cùng
        valid_comms = [comm for comm in level_communities.values() if len(comm["nodes"]) > 0]
        final_communities.extend(valid_comms)

        # ================= CHUẨN BỊ CHO LEVEL TIẾP THEO =================
        logging.info(f"Đang gập (collapse) đồ thị để chuẩn bị cho Level {current_level + 1}...")
        
        # Gập đồ thị: Các node cùng cộng đồng sẽ bị nhào nặn thành 1 Siêu nút
        current_graph.contract_vertices(partition.membership)
        
        # Gộp các cạnh trùng nhau giữa các Siêu nút và CỘNG DỒN trọng số (weight)
        current_graph.simplify(combine_edges={"weight": "sum"})
        
        # --- THÊM MỚI BẮT ĐẦU: Chuẩn hóa trọng số và cập nhật Resolution ---
        # 1. Log-scaling: Làm mượt sự chênh lệch trọng số khổng lồ giữa các siêu nút
        for edge in current_graph.es:
            edge["weight"] = math.log10(edge["weight"] + 1) + 1
            
        # 2. Giảm resolution để ép thuật toán tìm các cộng đồng LỚN HƠN ở Level tiếp theo
        # Hệ số 0.8 có nghĩa là giảm 20% mỗi level (Bạn có thể tinh chỉnh từ 0.5 - 0.9 tùy dữ liệu)
        
        # current_resolution = current_resolution * 0.8

        current_resolution = current_resolution / 10.0

        # --- THÊM MỚI KẾT THÚC ---

        # Chuẩn bị mapping cho vòng lặp sau
        node_to_prev_comm = node_to_curr_comm
        prev_level_comm_ids = [level_communities[i]["community_id"] for i in range(num_communities)]
        current_level += 1

    # 6. Lưu kết quả
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_communities, f, ensure_ascii=False, indent=4)
        
    logging.info(f"Đã lưu thành công {len(final_communities)} communities vào {OUTPUT_FILE}")
    logging.info("--- HOÀN TẤT ---")

if __name__ == "__main__":
    main()