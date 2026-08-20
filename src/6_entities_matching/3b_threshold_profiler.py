import json
import os
import re
import pandas as pd
from rapidfuzz.distance import Levenshtein
from collections import defaultdict

DATA_DIR = r"C:\1. Project\ĐATN\Data\07_Entities_matching"
INPUT_FILE = os.path.join(DATA_DIR, "2_rule_based_out", "entities_after_rules.json")
REPORT_FILE = os.path.join(DATA_DIR, "3_fuzzy_out", "threshold_sweep_report.csv")

def extract_critical_identifiers(text):
    numbers = re.findall(r'\d+', text)
    letters = re.findall(r'\b[A-Z]\b', text)
    romans = re.findall(r'\b(?:I{1,4}|IV|V|VI{1,3}|IX|X{1,3}|IVS)\b', text)
    critical_vocab = 'NÃO|NẤM|THỊ|VỊ|KHỨU|THÍNH|XÚC|TRÁI|PHẢI|TRÊN|DƯỚI|TRONG|NGOÀI|TRƯỚC|SAU|TĨNH|ĐỘNG|CẤP|MẠN|ÂM|DƯƠNG|LÀNH|ÁC|TIM|GAN|PHỔI|THẬN|MẬT|MÁU|MỦ|MẮT|MŨI|MIỆNG|TAI|CỔ|HỌNG|NGỰC|BỤNG|LƯNG|TAY|CHÂN|DA|CƠ|MỠ|XƯƠNG|KHỚP'
    vocabs = re.findall(fr'\b(?:{critical_vocab})\b', text)
    return set(numbers + letters + romans + vocabs)

def has_critical_mismatch(ent1, ent2):
    return extract_critical_identifiers(ent1) != extract_critical_identifiers(ent2)

class DSU:
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
        if root_i != root_j: self.parent[root_i] = root_j

with open(INPUT_FILE, 'r', encoding='utf-8') as f:
    entities = json.load(f)

# Phân khối dữ liệu (Blocking) với Alphanumeric Fingerprint
blocks = defaultdict(list)
for ent in entities:
    clean_str = re.sub(r'[^A-Z0-9]', '', ent)
    key = clean_str[:4] if len(clean_str) >= 4 else clean_str
    blocks[key].append(ent)

thresholds = [80, 83, 85, 88, 90, 92, 94]
results = []

for t in thresholds:
    dsu = DSU(entities)
    for block_entities in blocks.values():
        n = len(block_entities)
        for i in range(n):
            for j in range(i + 1, n):
                ent1, ent2 = block_entities[i], block_entities[j]
                if has_critical_mismatch(ent1, ent2):
                    continue
                if Levenshtein.normalized_similarity(ent1, ent2) * 100 >= t:
                    dsu.union(ent1, ent2)
    
    unique_nodes = len(set(dsu.find(ent) for ent in entities))
    merged_nodes = len(entities) - unique_nodes
    results.append({"Threshold": t, "Unique_Nodes": unique_nodes, "Merged_Nodes": merged_nodes})

pd.DataFrame(results).to_csv(REPORT_FILE, index=False)
print(f"📊 Đã xuất ma trận quét ngưỡng vào: {REPORT_FILE}")