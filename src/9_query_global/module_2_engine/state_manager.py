# Chịu trách nhiệm load file JSONL vào RAM (hoặc kết nối NoSQL), xáo trộn (shuffle) và phân chunk (pack) dữ liệu.
import json
import random
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class ContextPacker:
    """
    Class quản lý trạng thái dữ liệu và đóng gói ngữ cảnh (Context Packing)
    cho pha Map của GraphRAG.
    """
    def __init__(self, target_level: int = 2, max_tokens_per_chunk: int = 3500):
        self.target_level = target_level
        self.max_tokens_per_chunk = max_tokens_per_chunk
        self.filtered_communities: List[Dict] = []
        
    def load_and_filter_data(self, jsonl_path: str):
        """Đọc file JSONL và chỉ giữ lại các community thuộc target_level."""
        logger.info(f"Đang tải dữ liệu từ {jsonl_path}...")
        try:
            with open(jsonl_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    # Chỉ lấy đúng Level được chỉ định
                    if data.get('level') == self.target_level:
                        self.filtered_communities.append(data)
                        
            logger.info(f"Đã lọc thành công {len(self.filtered_communities)} cộng đồng thuộc Level {self.target_level}.")
        except Exception as e:
            logger.error(f"Lỗi khi đọc file dữ liệu: {e}")
            raise

    def build_markdown_string(self, community: Dict) -> str:
        """Chuyển đổi 1 object JSON community thành chuỗi Markdown."""
        title = community.get('title', 'Không có tiêu đề')
        summary = community.get('summary', '')
        findings = community.get('findings', [])
        
        md_text = f"### [Cộng đồng {community.get('community_id', 'N/A')}] {title}\n"
        md_text += f"**Tóm tắt chung:** {summary}\n"
        
        if findings:
            md_text += "**Các phát hiện chi tiết:**\n"
            for finding in findings:
                f_summary = finding.get('summary', '')
                f_exp = finding.get('explanation', '')
                md_text += f"- {f_summary}: {f_exp}\n"
                
        md_text += "\n---\n"
        return md_text

    def pack_context_chunks(self) -> List[Dict]:
        """
        Xáo trộn và gộp (pack) các community thành các chunk.
        Trả về danh sách các chunk, mỗi chunk chứa nội dung văn bản và tổng token.
        """
        if not self.filtered_communities:
            logger.warning("Không có dữ liệu để pack. Vui lòng chạy load_and_filter_data trước.")
            return []

        # 1. Xáo trộn ngẫu nhiên (Shuffle) để tránh thiên lệch
        # Cố định seed trong lúc dev để dễ debug, khi deploy có thể bỏ seed
        random.seed(42) 
        random.shuffle(self.filtered_communities)
        
        chunks = []
        current_chunk_text = ""
        current_chunk_tokens = 0
        current_chunk_items = 0
        
        logger.info(f"Bắt đầu đóng gói (Packing) với giới hạn {self.max_tokens_per_chunk} tokens/chunk...")
        
        for comm in self.filtered_communities:
            tokens = comm.get('token_count', 0)
            
            # Kiểm tra nếu community này bản thân nó đã quá to (Edge case)
            if tokens > self.max_tokens_per_chunk:
                logger.warning(f"Community ID {comm.get('community_id')} có {tokens} tokens, vượt quá giới hạn chunk. Đang bỏ qua...")
                continue
                
            # Nếu nhét thêm community này mà VƯỢT ngưỡng -> Đóng chunk hiện tại lại
            if current_chunk_tokens + tokens > self.max_tokens_per_chunk:
                chunks.append({
                    "chunk_id": len(chunks) + 1,
                    "content": current_chunk_text,
                    "total_tokens": current_chunk_tokens,
                    "num_communities": current_chunk_items
                })
                # Reset lại chunk mới
                current_chunk_text = ""
                current_chunk_tokens = 0
                current_chunk_items = 0
                
            # Nhét community vào chunk hiện tại
            current_chunk_text += self.build_markdown_string(comm)
            current_chunk_tokens += tokens
            current_chunk_items += 1
            
        # 2. Đừng quên đẩy chunk cuối cùng (nếu còn sót lại data) vào list
        if current_chunk_items > 0:
            chunks.append({
                "chunk_id": len(chunks) + 1,
                "content": current_chunk_text,
                "total_tokens": current_chunk_tokens,
                "num_communities": current_chunk_items
            })
            
        logger.info(f"Đóng gói hoàn tất! Tạo ra {len(chunks)} chunks.")
        
        # In preview cấu trúc chunk
        if chunks:
            logger.info(f"[Preview Chunk 1]: {chunks[0]['num_communities']} communities, {chunks[0]['total_tokens']} tokens.")
            
        return chunks

# ==========================================
# Code test thử nghiệm nhanh (Có thể xóa khi tích hợp)
# ==========================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    TEST_PATH = r"C:\1. Project\ĐATN\Data\09_Communities_summaries\summaries_final.jsonl"
    
    packer = ContextPacker(target_level=2, max_tokens_per_chunk=3500)
    packer.load_and_filter_data(TEST_PATH)
    final_chunks = packer.pack_context_chunks()
    
    print("\n--- TEST: Nội dung của Chunk cuối cùng ---")
    print(final_chunks[0]['content'][:5000] + "...\n[ĐÃ CẮT BỚT ĐỂ HIỂN THỊ]")