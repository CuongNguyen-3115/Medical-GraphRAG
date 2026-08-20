import asyncio
import os
from data_loader import load_and_filter_communities
from summarizer import generate_community_summary
from checkpoint_manager import load_completed_ids, save_summary_checkpoint
from llm_client import GROQ_KEYS

# Giới hạn luồng (Concurrency) dựa trên số lượng key Groq.
# Nhân 2 lên để đẩy tốc độ, vì Groq xử lý rất nhanh và có cơ chế chờ khi đụng 429.
# CONCURRENCY_LIMIT = max(2, len(GROQ_KEYS) * 2)
CONCURRENCY_LIMIT = 1  # Ép chạy tuần tự từng cụm một để kiểm soát dễ dàng

VIP_FILE = "C:\\1. Project\\ĐATN\\Data\\09_Communities_summaries\\truncated_vip_ids.txt"
FAILED_VIP_FILE = "C:\\1. Project\\ĐATN\\Data\\09_Communities_summaries\\failed_vip_ids.txt"

async def process_vip_community(community: dict, semaphore: asyncio.Semaphore):
    async with semaphore:
        comm_id = community.get('community_id')
        
        while True: 
            result, status = await generate_community_summary(community, is_vip=True)
            
            if status == "SUCCESS" and result:
                actual_tokens = result.pop("_actual_tokens", "N/A")
                model_used = result.pop("_model", "Unknown")
                save_summary_checkpoint(comm_id, result)
                print(f"[VIP +] Xong ID {comm_id:<5} | Model: {model_used:<15} | Tokens: {actual_tokens}")
                break 
                
            elif status == "GLOBAL_EXHAUSTED":
                print(f"[VIP *] (Ngủ đông) - ID {comm_id} đang chờ tài nguyên hồi phục. Ngủ 60 giây...")
                await asyncio.sleep(60) 
                continue 

            elif status in ("VIP_FAILED", "TRUNCATED", "PARSE_ERROR"):
                print(f"   [VIP !] JSON lỗi kéo dài. Đưa ID {comm_id} vào danh sách failed_vip_ids.txt để chạy tay.")
                with open(FAILED_VIP_FILE, "a") as f:
                    f.write(f"{comm_id}\n")
                break 

            else:
                break

async def process_single_community(community: dict, semaphore: asyncio.Semaphore):
    async with semaphore:
        comm_id = community.get('community_id')
        
        while True: # Vòng lặp kiên trì
            # Hàm sinh báo cáo giờ trả về 2 biến
            result, status = await generate_community_summary(community)
            
            if status == "SUCCESS" and result:
                actual_tokens = result.pop("_actual_tokens", "N/A")
                model_used = result.pop("_model", "Unknown")
                save_summary_checkpoint(comm_id, result)
                print(f"[+] Xong ID {comm_id:<5} | Model: {model_used:<15} | Tokens: {actual_tokens}")
                break # Xong thì thoát vòng lặp
                
            elif status == "GLOBAL_EXHAUSTED":
                # Hệ thống sập toàn tập do hết Quota. Ngủ 60s rồi đánh lại chính cụm này.
                print(f"[*] (Ngủ đông) - ID {comm_id} đang chờ tài nguyên hồi phục. Ngủ 60 giây...")
                await asyncio.sleep(60) # Ngủ 1 phút để chắc chắn tài nguyên đã được refill
                print(f"[*] (Thức dậy) - Thử lại ID {comm_id}...")
                continue # Lặp lại vòng quay

            # --- THÊM KHỐI LỆNH NÀY ---
            elif status == "TRUNCATED":
                print(f"   [!] Đưa ID {comm_id} vào danh sách VIP (Cụm Siêu To) để xử lý riêng.")
                # Ghi nối (append) ID vào file txt
                with open("C:\\1. Project\\ĐATN\\Data\\09_Communities_summaries\\truncated_vip_ids.txt", "a") as f:
                    f.write(f"{comm_id}\n")
                break # Thoát vòng lặp, chạy cụm tiếp theo
            # ---------------------------

            else:
                break
                
            
async def main_async():
    print("================================================================")
    print("       KÍCH HOẠT CHECKPOINT 3: TRI-LAYER BATCH PROCESSING       ")
    print(f"       Luồng song song (Concurrency): {CONCURRENCY_LIMIT}")
    print("================================================================")
    
    process_list, _ = load_and_filter_communities()
    if not process_list:
        print("[-] Không có dữ liệu để xử lý.")
        return
        
    completed_ids = load_completed_ids()
    if completed_ids:
        print(f"[*] Phục hồi: Tìm thấy {len(completed_ids)} cụm đã xong từ Checkpoint.")

    # Đọc danh sách VIP
    vip_ids = set()
    if os.path.exists(VIP_FILE):
        with open(VIP_FILE, 'r') as f:
            vip_ids = {int(line.strip()) for line in f if line.strip().isdigit()}
            
    # Lọc những cụm VIP đã xong
    pending_vip_ids = vip_ids - completed_ids
    
    # Ghi đè lại file file VIP (xóa những cụm đã hoàn thành)
    if os.path.exists(VIP_FILE):
        with open(VIP_FILE, 'w') as f:
            for vid in pending_vip_ids:
                f.write(f"{vid}\n")
                
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    
    # 1. TIẾN HÀNH XỬ LÝ CỤM VIP TRƯỚC TIÊN
    if pending_vip_ids:
        print(f"\n[*] Phát hiện {len(pending_vip_ids)} cụm VIP. Kích hoạt Model sức mạnh cao (Max Tokens: 2048)...")
        vip_tasks = [process_vip_community(c, semaphore) for c in process_list if c.get('community_id') in pending_vip_ids]
        await asyncio.gather(*vip_tasks)
        print("[*] Đã xử lý xong lô VIP (Cụm Siêu To)!\n")
        
        # Tải lại ID hoàn thành sau khi chạy VIP
        completed_ids = load_completed_ids()
        
    # Ngăn việc chạy cày lại các cụm VIP bị FAILED
    failed_vip_ids = set()
    if os.path.exists(FAILED_VIP_FILE):
        with open(FAILED_VIP_FILE, 'r') as f:
            failed_vip_ids = {int(line.strip()) for line in f if line.strip().isdigit()}
        
    tasks_to_run = [c for c in process_list if c.get('community_id') not in completed_ids and c.get('community_id') not in pending_vip_ids and c.get('community_id') not in failed_vip_ids]
    # Sắp xếp theo community_id từ bé đến lớn để chạy tịnh tiến
    tasks_to_run.sort(key=lambda x: x.get('community_id', 0))
    
    print(f"[*] Số lượng cụm cần cày trong phiên này: {len(tasks_to_run)}")
    if not tasks_to_run:
        print("[+] Tuyệt vời! Toàn bộ đồ thị đã được tóm tắt hoàn tất.")
        return

    tasks = [process_single_community(comm, semaphore) for comm in tasks_to_run]
    
    print("\n[*] Đang nổ máy dây chuyền sản xuất...")
    await asyncio.gather(*tasks)
    
    print("================================================================")
    print("Hoàn tất phiên chạy!")

if __name__ == "__main__":
    asyncio.run(main_async())