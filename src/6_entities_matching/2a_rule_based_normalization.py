# Xử lý theo luật Regex
import json
import re
import os

DATA_DIR = r"C:\1. Project\ĐATN\Data\07_Entities_matching"
INPUT_NODES = os.path.join(DATA_DIR, "0_exact_matched", "exact_matched_nodes.json")
INPUT_EDGES = os.path.join(DATA_DIR, "0_exact_matched", "exact_matched_edges.json")

OUT_DIR = os.path.join(DATA_DIR, "2_rule_based_out")
os.makedirs(OUT_DIR, exist_ok=True)

OUT_NODES = os.path.join(OUT_DIR, "rule_based_nodes.json")
OUT_EDGES = os.path.join(OUT_DIR, "rule_based_edges.json")
OUTPUT_ENTITIES_LIST = os.path.join(OUT_DIR, "entities_after_rules.json")
MAPPING_OUTPUT_FILE = os.path.join(OUT_DIR, "rule_based_mapping.json")

RULES_CONFIG_PATH = r"C:\1. Project\ĐATN\src\6_entities_matching\rules_config.json"

# Giả lập hoặc nạp file viết tắt của bạn
VALID_ABBREVIATIONS = {"D", "E", "S", "CK", "EF", "LH", "HB", "XQ"}
CLINICAL_ACTIONS = ["XỊT", "UỐNG", "TIÊM", "NGƯNG", "TĂNG", "LIỀU", "NGƯỜI LỚN", "TRẺ EM", "TRUYỀN TĨNH MẠCH"]

def load_regex_rules():
    if os.path.exists(RULES_CONFIG_PATH):
        with open(RULES_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

REGEX_RULES = load_regex_rules()

def advanced_structural_clean(text):
    text = text.upper().strip()
    
    if "ENTITY" in text or "#### (" in text:
        return None
        
    letters = re.findall(r"[A-ZÀ-Ỹ]", text)
    total_chars = len(text)
    acr = len(letters) / total_chars if total_chars > 0 else 0
    if total_chars > 4 and acr < 0.25:
        return None

    # Strip ALL formatting artifacts such as Markdown Hashes everywhere, asterisks, brackets when hanging
    text = re.sub(r"#+", " ", text)
    text = re.sub(r"\*+", " ", text)
    text = re.sub(r"[{}\[\]_><]", " ", text) # remove special brackets, underscores
    text = re.sub(r"\$", "", text)
    text = re.sub(r"(?<=[A-Z])\s+(?=\d)", "", text)
    text = re.sub(r"\^-", "-", text)
    text = re.sub(r"\s{2,}", " ", text)
    text = text.strip()
    
    if len(text) == 0:
        return None
    return text

def clean_text_with_rules(text):
    text = text.upper().strip()
    
    text = re.sub(r"</\|>", " ", text)
    text = re.sub(r"\[\s*O\s*\]\s*C", "°C", text)
    text = re.sub(r"ĐỘ\s+C\b", "°C", text)
    
    for pattern, replacement in REGEX_RULES.items():
        text = re.sub(pattern, replacement, text)
    
    text = text.replace("DIHYDROXY VITAMIN", "DIHYDROXYVITAMIN")
    text = re.sub(r"\b(.+?)(?:\s+\1)+\b", r"\1", text)
    text = re.sub(r"\s{2,}", " ", text)
    
    return text.strip()

def process_outliers(entities_list):
    processed_nodes = set()
    mapping_dict = {}
    
    for entity in entities_list:
        structured_clean = advanced_structural_clean(entity)
        if not structured_clean:
            mapping_dict[entity] = None
            continue
            
        cleaned = clean_text_with_rules(structured_clean)
        length = len(cleaned)
        
        if length == 0:
            mapping_dict[entity] = None
            continue
            
        if length <= 2:
            if cleaned.isdigit():
                mapping_dict[entity] = None
                continue
            if re.match(r"^[TNM][0-4X]$", cleaned) or cleaned in VALID_ABBREVIATIONS or length == 2:
                processed_nodes.add(cleaned)
                mapping_dict[entity] = cleaned
            else:
                mapping_dict[entity] = None
            continue
            
        if length > 60:
            if "," in cleaned and length > 150:
                sub_entities = cleaned.split(",")
                valid_subs = []
                for sub in sub_entities:
                    sub_cleaned = clean_text_with_rules(sub)
                    if len(sub_cleaned) > 2:
                        processed_nodes.add(sub_cleaned)
                        valid_subs.append(sub_cleaned)
                mapping_dict[entity] = valid_subs if valid_subs else None
                continue
            
            if any(action in cleaned for action in CLINICAL_ACTIONS):
                mapping_dict[entity] = None
                continue
                
        processed_nodes.add(cleaned)
        mapping_dict[entity] = cleaned
        
    return sorted(list(processed_nodes)), mapping_dict

def update_graph(nodes, edges, mapping_dict):
    new_nodes_dict = {}
    
    for node in nodes:
        old_name = node["entity_name"]
        mapped_values = mapping_dict.get(old_name, old_name)
        
        if mapped_values is None:
            continue
            
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
        
        if map_src is None or map_tgt is None:
            continue
            
        srcs = map_src if isinstance(map_src, list) else [map_src]
        tgts = map_tgt if isinstance(map_tgt, list) else [map_tgt]
        
        for s in srcs:
            for t in tgts:
                if s == t:
                    continue
                    
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

if __name__ == "__main__":
    print("⏳ Đang tải đồ thị gốc từ 0_exact_matched...")
    with open(INPUT_NODES, "r", encoding="utf-8") as f:
        raw_nodes = json.load(f)
    with open(INPUT_EDGES, "r", encoding="utf-8") as f:
        raw_edges = json.load(f)
        
    print(f"📥 Tổng số lượng Nodes gốc: {len(raw_nodes)}")
    print(f"📥 Tổng số lượng Edges gốc: {len(raw_edges)}")
    
    # Trích xuất toàn bộ entity unique từ cả Nodes và Edges
    raw_entities_set = set([n["entity_name"] for n in raw_nodes])
    for edge in raw_edges:
        raw_entities_set.add(edge["source"])
        raw_entities_set.add(edge["target"])
    raw_entities = list(raw_entities_set)
    
    print(f"📥 Tổng thực thể Entity Names cần chuẩn hóa (từ Nodes và Edges): {len(raw_entities)}")
    
    final_entities, mapping_dict = process_outliers(raw_entities)
    print(f"📤 Tổng thực thể sạch sau Rule-based: {len(final_entities)}")
    
    print("⏳ Đang cập nhật đồ thị bằng Mapping log...")
    new_nodes, new_edges = update_graph(raw_nodes, raw_edges, mapping_dict)
    
    print(f"📤 Tổng Nodes sau Rule-based Phase 2: {len(new_nodes)}")
    print(f"📤 Tổng Edges sau Rule-based Phase 2: {len(new_edges)}")
    print(f"📉 Đã giảm tải: {len(raw_nodes) - len(new_nodes)} Nodes và {len(raw_edges) - len(new_edges)} Edges lỗi/trùng lặp.")
    
    with open(OUTPUT_ENTITIES_LIST, "w", encoding="utf-8") as f:
        json.dump(final_entities, f, ensure_ascii=False, indent=4)
        
    with open(MAPPING_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(mapping_dict, f, ensure_ascii=False, indent=4)
        
    with open(OUT_NODES, "w", encoding="utf-8") as f:
        json.dump(new_nodes, f, ensure_ascii=False, indent=4)
        
    with open(OUT_EDGES, "w", encoding="utf-8") as f:
        json.dump(new_edges, f, ensure_ascii=False, indent=4)
        
    print("💾 Đã lưu toàn bộ Cấu trúc Graph mới và Mapping Regex vào thư mục 2_rule_based_out!")

