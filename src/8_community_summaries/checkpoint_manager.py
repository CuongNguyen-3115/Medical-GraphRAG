import json
from pathlib import Path
from config import OUTPUT_SUMMARIES_DIR

CHECKPOINT_FILE = OUTPUT_SUMMARIES_DIR / "summaries_checkpoint.jsonl"

def load_completed_ids() -> set:
    completed_ids = set()
    if not CHECKPOINT_FILE.exists():
        return completed_ids
        
    with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    if "community_id" in data:
                        completed_ids.add(data["community_id"])
                except json.JSONDecodeError:
                    continue
    return completed_ids

def save_summary_checkpoint(community_id: int, summary_data: dict):
    # Tạo dictionary mới với community_id nằm ở vị trí đầu tiên
    ordered_data = {"community_id": community_id}
    ordered_data.update(summary_data)
    
    with open(CHECKPOINT_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(ordered_data, ensure_ascii=False) + "\n")