import json
from neo4j import GraphDatabase

# Cấu hình kết nối tới Neo4j Desktop local
URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = "12345678" # Thay bằng mật khẩu bạn đã đặt

# Đường dẫn file của bạn
NODES_PATH = r"C:\1. Project\ĐATN\Data\07_Entities_matching\6_graph_final\nodes.json"
EDGES_PATH = r"C:\1. Project\ĐATN\Data\07_Entities_matching\6_graph_final\edges.json"

def create_constraints(tx):
    """Tạo chỉ mục (Index) và Ràng buộc (Constraint) để truy vấn và import siêu tốc"""
    # Đảm bảo mỗi Entity có một cái tên duy nhất và tra cứu nhanh
    tx.run("CREATE CONSTRAINT IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE")
    tx.run("CREATE CONSTRAINT IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE")

def import_nodes(tx, nodes_data):
    """Đẩy danh sách Node vào Neo4j"""
    query = """
    UNWIND $nodes AS n
    MERGE (e:Entity {name: n.entity_name})
    SET e.id = n.id,
        e.types = n.entity_types,
        e.description = n.descriptions,
        e.weight = n.occurrence_count
    """
    tx.run(query, nodes=nodes_data)

def import_edges(tx, edges_data):
    """Đẩy danh sách Cạnh (Mối quan hệ) vào Neo4j"""
    query = """
    UNWIND $edges AS rel
    MATCH (source:Entity {name: rel.source})
    MATCH (target:Entity {name: rel.target})
    MERGE (source)-[r:RELATED_TO]->(target)
    SET r.description = rel.descriptions,
        r.weight = rel.weight
    """
    tx.run(query, edges=edges_data)

def main():
    # 1. Đọc dữ liệu JSON
    with open(NODES_PATH, 'r', encoding='utf-8') as f:
        nodes = json.load(f)
    with open(EDGES_PATH, 'r', encoding='utf-8') as f:
        edges = json.load(f)

    print(f"Đã nạp {len(nodes)} nodes và {len(edges)} edges từ bộ nhớ.")

    # 2. Kết nối Neo4j và thực thi
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    with driver.session() as session:
        print("Đang tạo Constraints...")
        session.execute_write(create_constraints)
        
        print("Đang Import Nodes...")
        session.execute_write(import_nodes, nodes)
        
        print("Đang Import Edges...")
        session.execute_write(import_edges, edges)

    driver.close()
    print("✅ Hoàn tất việc đưa Đồ thị lên Neo4j!")

if __name__ == "__main__":
    main()