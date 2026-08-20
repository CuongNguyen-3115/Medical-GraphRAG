import json
import os
import networkx as nx
from pyvis.network import Network

# --- CẤU HÌNH ĐƯỜNG DẪN (Bạn có thể cập nhật lại theo path máy bạn) ---
BASE_DIR = r"C:\1. Project\ĐATN"
NODES_PATH = os.path.join(BASE_DIR, "Data", "07_Entities_matching", "3_fuzzy_out", "fuzzy_matched_nodes.json")
EDGES_PATH = os.path.join(BASE_DIR, "Data", "07_Entities_matching", "3_fuzzy_out", "fuzzy_matched_edges.json")
COMMUNITIES_PATH = os.path.join(BASE_DIR, "Data", "08_Communities_detecting", "communities.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "Data", "Visualizations")

os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def build_networkx_graph(nodes_data, edges_data):
    """Xây dựng đồ thị NetworkX gốc"""
    G = nx.Graph()
    for node in nodes_data:
        G.add_node(node["entity_name"], **node)
    for edge in edges_data:
        if edge.get("source") and edge.get("target"):
            G.add_edge(edge["source"], edge["target"], weight=edge.get("weight", 1.0))
    return G

# ================= GÓC NHÌN 1: FULL GRAPH CHO GEPHI =================
def export_full_graph_for_gephi(G):
    print("\n[1] Đang xuất Toàn cảnh (Full Graph) ra định dạng GraphML cho Gephi...")
    output_file = os.path.join(OUTPUT_DIR, "Full_Graph_Gephi.graphml")
    
    G_export = G.copy()
    for n, data in G_export.nodes(data=True):
        for k, v in data.items():
            if isinstance(v, (list, dict)):
                G_export.nodes[n][k] = str(v)
    for u, v, data in G_export.edges(data=True):
        for k, val in data.items():
            if isinstance(val, (list, dict)):
                G_export.edges[u][v][k] = str(val)
                
    nx.write_graphml(G_export, output_file)
    print(f"--> Đã lưu: {output_file}")

# ================= GÓC NHÌN 2: NODE-LEVEL (Màu theo Cộng đồng) =================
def visualize_node_level_communities(G, communities_data, target_level=4, top_n=500):
    print(f"\n[2] Đang tạo Node-Level Graph (Tô màu Cộng đồng Level {target_level})...")
    output_html = os.path.join(OUTPUT_DIR, f"View_NodeLevel_Comm_Lv{target_level}.html")
    
    target_comms = [c for c in communities_data if c.get("level") == target_level]
    node_to_comm = {}
    for comm in target_comms:
        comm_id = comm["community_id"]
        for node in comm["nodes"]:
            node_to_comm[node["entity_name"]] = str(comm_id)

    degrees = dict(G.degree())
    top_nodes = sorted(degrees.keys(), key=lambda x: degrees[x], reverse=True)[:top_n]
    subgraph = G.subgraph(top_nodes)

    net = Network(height="800px", width="100%", bgcolor="#ffffff", font_color="black", cdn_resources='remote')
    
    for node_name in subgraph.nodes():
        node_degree = degrees[node_name]
        node_size = min(10 + (node_degree * 0.5), 50)
        comm_id = node_to_comm.get(node_name, "Unknown")
        title = f"Thực thể: {node_name}\nCộng đồng ID: {comm_id}\nConnections: {node_degree}"
        net.add_node(node_name, label=node_name, title=title, size=node_size, group=comm_id)

    for u, v, data in subgraph.edges(data=True):
        net.add_edge(u, v, value=data.get("weight", 1))

    net.repulsion(node_distance=200, spring_length=200)
    net.save_graph(output_html)
    print(f"--> Đã lưu: {output_html}")

# ================= GÓC NHÌN 3: MACRO-LEVEL (Đồ thị Siêu Nút) =================
def visualize_macro_level_communities(G, communities_data, target_level=4):
    print(f"\n[3] Đang tạo Macro-Level Graph (Đồ thị Chủ đề Level {target_level})...")
    output_html = os.path.join(OUTPUT_DIR, f"View_MacroLevel_Comm_Lv{target_level}.html")
    
    target_comms = [c for c in communities_data if c.get("level") == target_level]
    
    # 1. Tạo mapping Entity -> Community ID
    node_to_comm = {}
    comm_sizes = {}
    for comm in target_comms:
        c_id = str(comm["community_id"])
        comm_sizes[c_id] = len(comm["nodes"])
        for node in comm["nodes"]:
            node_to_comm[node["entity_name"]] = c_id

    # 2. Xây dựng đồ thị Siêu nút (Macro Graph)
    MG = nx.Graph()
    for c_id, size in comm_sizes.items():
        MG.add_node(c_id, size=size)

    # Đếm số lượng liên kết chéo giữa các cộng đồng
    for u, v, data in G.edges(data=True):
        cu = node_to_comm.get(u)
        cv = node_to_comm.get(v)
        
        # Chỉ vẽ cạnh kết nối 2 cộng đồng KHÁC NHAU
        if cu and cv and cu != cv:
            if MG.has_edge(cu, cv):
                MG[cu][cv]['weight'] += data.get('weight', 1)
            else:
                MG.add_edge(cu, cv, weight=data.get('weight', 1))

    # 3. Vẽ đồ thị bằng PyVis
    net = Network(height="800px", width="100%", bgcolor="#222222", font_color="white", cdn_resources='remote')
    
    for comm_id in MG.nodes():
        size = MG.nodes[comm_id]['size']
        # Node càng nhiều entity thì kích thước càng to
        node_size = min(15 + (size * 0.2), 80)
        title = f"Cộng đồng ID: {comm_id}\nTổng số thực thể: {size}"
        net.add_node(comm_id, label=f"Comm {comm_id}", title=title, size=node_size, group=comm_id)

    for u, v, data in MG.edges(data=True):
        weight = data['weight']
        edge_width = min(weight * 0.5, 15) # Giới hạn độ dày của cạnh
        tooltip = f"Liên kết chéo: {weight} edges"
        net.add_edge(u, v, value=edge_width, title=tooltip)

    net.repulsion(node_distance=300, spring_length=300)
    net.save_graph(output_html)
    print(f"--> Đã lưu: {output_html}")

# ================= GÓC NHÌN 4: EGO GRAPH (Mạng Cục bộ) =================
def visualize_ego_graph(G, center_node_name, radius=1):
    print(f"\n[4] Đang tạo Ego Graph cho thực thể: '{center_node_name}'...")
    if center_node_name not in G:
        print(f"Thực thể '{center_node_name}' không tồn tại trong đồ thị!")
        return

    output_html = os.path.join(OUTPUT_DIR, f"View_EgoGraph_{center_node_name.replace(' ', '_')}.html")
    ego_subgraph = nx.ego_graph(G, center_node_name, radius=radius)
    
    net = Network(height="800px", width="100%", bgcolor="#222222", font_color="white", cdn_resources='remote')
    
    for node_name in ego_subgraph.nodes():
        is_center = (node_name == center_node_name)
        node_color = "#ff4d4d" if is_center else "#97c2fc"
        node_size = 40 if is_center else 20
        net.add_node(node_name, label=node_name, size=node_size, color=node_color)

    for u, v, data in ego_subgraph.edges(data=True):
        net.add_edge(u, v, value=data.get("weight", 1))

    net.repulsion(node_distance=150)
    net.save_graph(output_html)
    print(f"--> Đã lưu: {output_html}")

def main():
    print("--- BẮT ĐẦU KẾT XUẤT ĐỒ THỊ 4 GÓC NHÌN ---")
    nodes_data = load_json(NODES_PATH)
    edges_data = load_json(EDGES_PATH)
    communities_data = load_json(COMMUNITIES_PATH)

    G = build_networkx_graph(nodes_data, edges_data)
    print(f"Đã nạp đồ thị gốc: {G.number_of_nodes()} đỉnh, {G.number_of_edges()} cạnh.")

    # Xuất 4 góc nhìn
    export_full_graph_for_gephi(G)
    visualize_node_level_communities(G, communities_data, target_level=4, top_n=500)
    visualize_macro_level_communities(G, communities_data, target_level=4)
    
    # Ego Graph (Lấy node có degree lớn nhất làm ví dụ)
    if len(G.nodes) > 0:
        top_node = sorted(G.degree, key=lambda x: x[1], reverse=True)[0][0]
        visualize_ego_graph(G, center_node_name=top_node, radius=2)

    print("\n--- HOÀN TẤT ---")

if __name__ == "__main__":
    main()