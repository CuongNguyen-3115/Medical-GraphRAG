import json
import os
import time
import re
from collections import defaultdict
from rapidfuzz.distance import Levenshtein

DATA_DIR = r"C:\1. Project\ĐATN\Data\07_Entities_matching"
INPUT_FILE = os.path.join(DATA_DIR, "2_rule_based_out", "entities_after_rules.json")
INPUT_NODES = os.path.join(DATA_DIR, "2_rule_based_out", "rule_based_nodes.json")
INPUT_EDGES = os.path.join(DATA_DIR, "2_rule_based_out", "rule_based_edges.json")

OUTPUT_DIR = os.path.join(DATA_DIR, "3_fuzzy_out")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "entities_after_fuzzy.json")
MAPPING_FILE = os.path.join(OUTPUT_DIR, "fuzzy_mapping_report.json")
OUT_NODES = os.path.join(OUTPUT_DIR, "fuzzy_matched_nodes.json")
OUT_EDGES = os.path.join(OUTPUT_DIR, "fuzzy_matched_edges.json")

os.makedirs(OUTPUT_DIR, exist_ok=True)
SIMILARITY_THRESHOLD = 90.0 

def extract_critical_identifiers(text):
    """
    Trích xuất các token mang tính phân loại cốt lõi trong y khoa:
    - Các chữ cái đơn cô lập (B, C, D, A, E...)
    - Tất cả các cụm chữ số (1, 2, 3, 500, 250...) dù đứng riêng hay dính liền
    - Số La Mã (I, II, III, IV, V, VI, IX, X, IVS...)
    - Các từ khóa chỉ định giải phẫu/đặc tính mang tính đối lập hoặc phân loại cao
    """
    numbers = re.findall(r'\d+', text)
    letters = re.findall(r'\b[A-Z]\b', text)
    romans = re.findall(r'\b(?:I{1,4}|IV|V|VI{1,3}|IX|X{1,3}|IVS)\b', text)
    
    # Từ khóa lâm sàng siêu nhạy cảm (1-2 âm tiết đổi nghĩa hoàn toàn)
    critical_vocab = 'NÃO|NẤM|THỊ|VỊ|KHỨU|THÍNH|XÚC|TRÁI|PHẢI|TRÊN|DƯỚI|TRONG|NGOÀI|TRƯỚC|SAU|TĨNH|ĐỘNG|CẤP|MẠN|ÂM|DƯƠNG|LÀNH|ÁC|TIM|GAN|PHỔI|THẬN|MẬT|MÁU|MỦ|MẮT|MŨI|MIỆNG|TAI|CỔ|HỌNG|NGỰC|BỤNG|LƯNG|TAY|CHÂN|DA|CƠ|MỠ|XƯƠNG|KHỚP'
    vocabs = re.findall(fr'\b(?:{critical_vocab})\b', text)
    
    return set(numbers + letters + romans + vocabs)

def has_critical_mismatch(ent1, ent2):
    """
    Hàm định lượng chặn đứng sai sót bắc cầu.
    Nếu tập hợp định danh (Identifiers) của hai chuỗi không khớp nhau tuyệt đối
    -> Báo vi phạm (True) để chặn đứng việc gộp cụm.
    """
    ids1 = extract_critical_identifiers(ent1)
    ids2 = extract_critical_identifiers(ent2)
    
    # THAY ĐỔI LOGIC: Thay vì check 'if ids1 and ids2', ta so sánh trực tiếp
    # Nếu hai tập định danh khác nhau (Ví dụ: {'1'} vs {'2'}, hoặc {'1'} vs set())
    # thì tuyệt đối không cho phép liên thông.
    if ids1 != ids2:
        return True # Phát hiện bất đồng định danh hoặc bất đối xứng thông tin
        
    return False # Đồng nhất thiết kế định danh (ví dụ: cùng là set() hoặc cùng là {'B'})

class DisjointSetUnion:
    def __init__(self, elements):
        self.parent = {el: el for el in elements}
    def find(self, i):
        path = []
        while self.parent[i] != i:
            path.append(i)
            i = self.parent[i]
        for node in path:
            self.parent[node] = i
        return i
    def union(self, i, j):
        root_i = self.find(i)
        root_j = self.find(j)
        if root_i != root_j:
            self.parent[root_i] = root_j

def find_canonical_name(cluster):
    if len(cluster) == 1: return list(cluster)[0]
    min_total_dist = float('inf')
    canonical_name = list(cluster)[0]
    for candidate in cluster:
        total_dist = 0
        for peer in cluster:
            if candidate != peer: total_dist += Levenshtein.distance(candidate, peer)
        if total_dist < min_total_dist:
            min_total_dist = total_dist
            canonical_name = candidate
    return canonical_name

def update_graph(nodes, edges, mapping_dict):
    new_nodes_dict = {}
    for node in nodes:
        old_name = node["entity_name"]
        mapped_values = mapping_dict.get(old_name, old_name)
        target_names = mapped_values if isinstance(mapped_values, list) else [mapped_values]
        for new_name in target_names:
            if new_name not in new_nodes_dict:
                new_nodes_dict[new_name] = {
                    "entity_name": new_name,
                    "entity_types": set(),
                    "descriptions": set(),
                    "source_chunks": set(),
                    "occurrence_count": 0
                }
            merged = new_nodes_dict[new_name]
            merged["entity_types"].update(node.get("entity_types", []))
            merged["descriptions"].update(node.get("descriptions", []))
            merged["source_chunks"].update(node.get("source_chunks", []))
            merged["occurrence_count"] += node.get("occurrence_count", 1)

    final_nodes = []
    for i, (name, data) in enumerate(new_nodes_dict.items(), 1):
        final_nodes.append({
            "id": i,
            "entity_name": name,
            "entity_types": list(data["entity_types"]),
            "descriptions": list(data["descriptions"]),
            "source_chunks": list(data["source_chunks"]),
            "occurrence_count": data["occurrence_count"]
        })

    new_edges_dict = {}
    for edge in edges:
        old_source = edge["source"]
        old_target = edge["target"]
        map_src = mapping_dict.get(old_source, old_source)
        map_tgt = mapping_dict.get(old_target, old_target)
        srcs = map_src if isinstance(map_src, list) else [map_src]
        tgts = map_tgt if isinstance(map_tgt, list) else [map_tgt]
        for s in srcs:
            for t in tgts:
                if s == t: continue
                pair = tuple(sorted([s, t]))
                if pair not in new_edges_dict:
                    new_edges_dict[pair] = {
                        "source": pair[0],
                        "target": pair[1],
                        "descriptions": set(),
                        "weight": 0,
                        "source_chunks": set()
                    }
                merged = new_edges_dict[pair]
                merged["descriptions"].update(edge.get("descriptions", []))
                merged["weight"] += edge.get("weight", 1)
                merged["source_chunks"].update(edge.get("source_chunks", []))

    final_edges = []
    for i, (pair, data) in enumerate(new_edges_dict.items(), 1):
        final_edges.append({
            "id": i,
            "source": data["source"],
            "target": data["target"],
            "descriptions": list(data["descriptions"]),
            "weight": data["weight"],
            "source_chunks": list(data["source_chunks"])
        })
    return final_nodes, final_edges

def get_clean_alphanumeric(text):
    """Lọc bỏ mọi khoảng trắng và ký tự đặc biệt, chỉ giữ lại chữ cái và số"""
    return re.sub(r'[^A-Z0-9À-Ỹ]', '', text)

def run_fuzzy_matching_v2():
    start_time = time.time()
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        entities = json.load(f)
    print(f"📥 Đã nạp {len(entities)} thực thể.")
    
    # Blocking (Cải tiến với Alphanumeric Fingerprint)
    blocks = defaultdict(list)
    for entity in entities:
        # Loại bỏ các ký tự dấu phẩy, gạch nối, khoảng trắng... chỉ giữ lại chữ số và chữ cái
        clean_str = re.sub(r'[^A-Z0-9]', '', entity)
        # Sử dụng 4 ký tự gốc đầu tiên làm chìa khóa gom khối (Fingerprint Prefix Blocking Key)
        key = clean_str[:4] if len(clean_str) >= 4 else clean_str
        blocks[key].append(entity)
        
    dsu = DisjointSetUnion(entities)
    
    for block_key, block_entities in blocks.items():
        n_block = len(block_entities)
        if n_block < 2: continue
            
        for i in range(n_block):
            for j in range(i + 1, n_block):
                ent1 = block_entities[i]
                ent2 = block_entities[j]
                
                # --- BẢN VÁ BẢO VỆ ĐỊNH LƯỢNG ---
                if has_critical_mismatch(ent1, ent2):
                    continue # Bỏ qua ngay lập tức, ép score về hiệu ứng cách ly
                
                # Cải tiến MDM: So sánh trên Data đã được Normalization (Xóa khoảng trắng, dấu câu)
                clean_ent1 = get_clean_alphanumeric(ent1)
                clean_ent2 = get_clean_alphanumeric(ent2)

                score = Levenshtein.normalized_similarity(clean_ent1, clean_ent2) * 100
                if score >= SIMILARITY_THRESHOLD:
                    dsu.union(ent1, ent2)
                    
    # Trích xuất kết quả
    clusters = defaultdict(set)
    for entity in entities:
        root = dsu.find(entity)
        clusters[root].add(entity)
        
    entity_mapping = {}
    final_unique_entities = set()
    
    for root, cluster_elements in clusters.items():
        canonical = find_canonical_name(cluster_elements)
        final_unique_entities.add(canonical)
        for element in cluster_elements:
            entity_mapping[element] = canonical

    # Ghi nhận các báo cáo
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(sorted(list(final_unique_entities)), f, ensure_ascii=False, indent=4)
    with open(MAPPING_FILE, 'w', encoding='utf-8') as f:
        json.dump(entity_mapping, f, ensure_ascii=False, indent=4)
        
    print("⏳ Đang tải nodes, edges để cập nhật đồ thị bằng Mapping log...")
    with open(INPUT_NODES, "r", encoding="utf-8") as f:
        raw_nodes = json.load(f)
    with open(INPUT_EDGES, "r", encoding="utf-8") as f:
        raw_edges = json.load(f)

    new_nodes, new_edges = update_graph(raw_nodes, raw_edges, entity_mapping)

    with open(OUT_NODES, "w", encoding="utf-8") as f:
        json.dump(new_nodes, f, ensure_ascii=False, indent=4)
    with open(OUT_EDGES, "w", encoding="utf-8") as f:
        json.dump(new_edges, f, ensure_ascii=False, indent=4)
        
    print("\n📊 ==================== BẢNG THỐNG KÊ FUZZY MATCHING V2 ====================")
    print(f"🔹 THỰC THỂ: Đầu vào (Input entities)    : {len(entities):,}")
    print(f"🔹 THỰC THỂ: Đầu ra  (Unique entities)   : {len(final_unique_entities):,}")
    print(f"📉 MỨC GIẢM: Lượng thực thể đã gộp lại   : {len(entities) - len(final_unique_entities):,} (Khử trùng lặp)")
    print("----------------------------------------------------------------------------")
    print(f"🔹 ĐỒ THỊ NODES: Trọng lượng Nodes gốc   : {len(raw_nodes):,}")
    print(f"🔹 ĐỒ THỊ NODES: Tối ưu (Fuzzy matched)  : {len(new_nodes):,}")
    print(f"📉 MỨC GIẢM NODES                        : {len(raw_nodes) - len(new_nodes):,}")
    print("----------------------------------------------------------------------------")
    print(f"🔹 ĐỒ THỊ EDGES: Trọng lượng Edges gốc   : {len(raw_edges):,}")
    print(f"🔹 ĐỒ THỊ EDGES: Tối ưu (Fuzzy matched)  : {len(new_edges):,}")
    print(f"📉 MỨC GIẢM EDGES                        : {len(raw_edges) - len(new_edges):,}")
    print("============================================================================\n")

    print(f"✅ Đã xuất Nodes chuẩn hóa  tại: {OUT_NODES}")
    print(f"✅ Đã xuất Edges chuẩn hóa  tại: {OUT_EDGES}")
    print(f"⏱️ Tổng thời gian chạy: {time.time() - start_time:.2f} giây.")

if __name__ == "__main__":
    run_fuzzy_matching_v2()