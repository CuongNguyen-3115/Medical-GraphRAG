import os
import asyncio
import time
import json
from dotenv import dotenv_values
from groq import AsyncGroq
from google import genai
from google.genai import types as genai_types
from openai import AsyncOpenAI
from huggingface_hub import AsyncInferenceClient

env_dict = dotenv_values(r"C:\1. Project\ĐATN\.env")
GROQ_KEYS = [v for k, v in env_dict.items() if k.startswith("GROQ_API_KEY") and v.strip()]
GEMINI_KEYS = [v for k, v in env_dict.items() if k.startswith("GEMINI_API_KEY") and v.strip()]
GITHUB_TOKEN = env_dict.get("GITHUB_TOKEN", "").strip()
HF_TOKEN = env_dict.get("HF_TOKEN", "").strip()
SAMBANOVA_TOKEN = env_dict.get("SAMBANOVA_API_KEY", "").strip()
CEREBRAS_TOKEN = env_dict.get("CEREBRAS_API_KEY", "").strip()

# ====================================================================
# UTILS: LOGGER CHI TIẾT
# ====================================================================
def log_action(item_id, action, provider, model, input_tok="N/A", output_tok="N/A", error=""):
    """Hàm log chuẩn hóa để theo dõi tiến trình và lỗi. item_id: ví dụ C0|NODE|171|TIM."""
    time_str = time.strftime("%H:%M:%S")
    log_msg = f"[{time_str}] | {str(item_id):<48} | {provider:<7} | {model:<25} | {action:<10}"
    if input_tok != "N/A" or output_tok != "N/A":
        log_msg += f" | In: {input_tok:<5} | Out: {output_tok:<4}"
    if error:
        log_msg += f" | Lỗi: {error}"
    print(log_msg)

# ====================================================================
# TẦNG 1: GROQ (Vắt kiệt từng Model -> từng Key)
# ====================================================================
class GroqManager:
    def __init__(self, keys):
        self.keys = keys
        self.clients = {key: AsyncGroq(api_key=key, max_retries=0) for key in keys}
        self.lock = asyncio.Lock()
        
        # Quản lý thời gian khóa theo từng model trên mỗi key
        self.model_limits = {}  # (key, model_id): unlock_time
        # Quản lý khoảng trễ cục bộ giữa các request của một key (tránh request dồn dập tpm)
        self.key_delays = {key: 0.0 for key in keys}

    async def get_client(self, model_id):
        """Trả về (Client, Key, WaitTime)."""
        async with self.lock:
            current_time = time.time()
            min_wait = float('inf')
            
            for key in self.keys:
                model_time = self.model_limits.get((key, model_id), 0.0)
                key_time = self.key_delays.get(key, 0.0)
                ready_time = max(model_time, key_time)
                
                if current_time >= ready_time:
                    return self.clients[key], key, 0.0
                
                wait = ready_time - current_time
                if wait < min_wait:
                    min_wait = wait
                    
            return None, None, min_wait

    async def report_rate_limit(self, key, model_id, reset_time_seconds, global_delay=0.0):
        """Khóa key theo model khi gặp 429, hoặc dãn cách request bằng global_delay."""
        async with self.lock:
            current_time = time.time()
            if reset_time_seconds > 0:
                self.model_limits[(key, model_id)] = current_time + float(reset_time_seconds)
            if global_delay > 0:
                self.key_delays[key] = current_time + float(global_delay)

groq_manager = GroqManager(GROQ_KEYS)

async def call_groq(system_prompt: str, user_prompt: str, comm_id: int, is_vip: bool = False) -> tuple[str, int, int, str]:
    """Trả về: (content, in_tokens, out_tokens, status). status: SUCCESS, 413, QUOTA_EXHAUSTED."""
    
    if is_vip:
        models_to_try = ["llama-3.3-70b-versatile", "meta-llama/llama-4-scout-17b-16e-instruct", "openai/gpt-oss-120b", "openai/gpt-oss-20b"]
        max_output_tokens = 2048
    else:
        models_to_try = [ "llama-3.3-70b-versatile", "meta-llama/llama-4-scout-17b-16e-instruct", "openai/gpt-oss-20b", "qwen/qwen3-32b", "openai/gpt-oss-120b", "llama-3.1-8b-instant", "groq/compound" ]
        max_output_tokens = 1024
    
    banned_models = set()
    
    while True:
        best_model = None
        client = None
        active_key = None
        min_wait = float('inf')
        
        # Chiến lược Tịnh tiến (Cascade): Tìm model "xịn nhất" đang rảnh Key
        for model_id in models_to_try:
            if model_id in banned_models: continue
            
            c, k, w = await groq_manager.get_client(model_id)
            if c is not None:
                best_model = model_id
                client = c
                active_key = k
                break # Cứ tìm thấy model xịn nhất có key là chộp liền
            if w < min_wait: min_wait = w
            
        if client is None:
            # Lập tức thoát để nhường cho tầng khác (như Github, Gemini...) thay vì kẹt chờ
            log_action(comm_id, "SKIPPED", "GROQ", "Toàn bộ", error=f"Hết Quota, chuyển tầng khác (Lock {min_wait:.1f}s)")
            break
            
        model_id = best_model
        log_action(comm_id, "TRYING", "GROQ", model_id)
        
        try:
            raw_response = await client.chat.completions.with_raw_response.create(
                model=model_id,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.1, max_tokens=max_output_tokens, top_p=0.9 
            )
            parsed = await raw_response.parse()
            in_tok = parsed.usage.prompt_tokens
            out_tok = parsed.usage.completion_tokens
            
            # Khóa chống spam 3 giây cho Key này
            await groq_manager.report_rate_limit(active_key, model_id, 0.0, global_delay=3.0)
            
            log_action(comm_id, "SUCCESS", "GROQ", model_id, in_tok, out_tok)
            return parsed.choices[0].message.content, in_tok, out_tok, "SUCCESS"
            
        except Exception as e:
            error_str = str(e)
            
            if "413" in error_str or "too large" in error_str.lower():
                log_action(comm_id, "FAILED", "GROQ", model_id, error="Lỗi 413 - Context quá lớn")
                banned_models.add(model_id) # Cấm model này vì đổi key cũng vô ích
                continue 
                
            if "rate_limit" in error_str or "tpm" in error_str.lower() or "429" in error_str:
                reset_time = 30.0
                try:
                    err_json = json.loads(error_str.split(" - ")[1].replace("'", '"'))
                    msg = err_json.get('error', {}).get('message', '')
                    if "try again in" in msg:
                        reset_time = float(msg.split("try again in ")[1].split("s")[0])
                except: pass
                
                await groq_manager.report_rate_limit(active_key, model_id, reset_time, global_delay=0.0)
                log_action(comm_id, "RATE_LIMIT", "GROQ", model_id, error=f"Khóa Key {active_key[:8]} {reset_time:.1f}s")
                continue # Trở lại vòng lặp While để tuột xuống các model nhẹ hơn hoặc dùng Key 2
            
            log_action(comm_id, "ERROR", "GROQ", model_id, error=error_str[:50])
            banned_models.add(model_id)
            continue
            
    return "", 0, 0, "QUOTA_EXHAUSTED"

# ====================================================================
# TẦNG 2 & TẦNG 3: (Giữ nguyên cấu trúc, thêm Logging)
# ====================================================================
class GeminiManager:
    def __init__(self, keys):
        self.keys = keys
        self.clients = {key: genai.Client(api_key=key) for key in keys}
        self.lock = asyncio.Lock()
        
        # Quản lý thời gian khóa theo từng model trên mỗi key
        self.model_limits = {}  # (key, model_id): unlock_time
        # Quản lý khoảng trễ cục bộ giữa các request của một key (RPM/TPM limit cơ bản của Gemini)
        self.key_delays = {key: 0.0 for key in keys}

    async def get_client(self, model_id):
        async with self.lock:
            current_time = time.time()
            min_wait = float('inf')
            
            for key in self.keys:
                model_time = self.model_limits.get((key, model_id), 0.0)
                key_time = self.key_delays.get(key, 0.0)
                ready_time = max(model_time, key_time)
                
                if current_time >= ready_time:
                    return self.clients[key], key, 0.0
                
                wait = ready_time - current_time
                if wait < min_wait:
                    min_wait = wait
                    
            return None, None, min_wait
            
    async def report_rate_limit(self, key, model_id, reset_time_seconds, global_delay=0.0):
        async with self.lock:
            current_time = time.time()
            if reset_time_seconds > 0:
                self.model_limits[(key, model_id)] = current_time + float(reset_time_seconds)
            if global_delay > 0:
                self.key_delays[key] = current_time + float(global_delay)

gemini_manager = GeminiManager(GEMINI_KEYS) if GEMINI_KEYS else None
    
# ĐOẠN CODE CẦN THAY THẾ CHO HÀM call_gemini
async def call_gemini(system_prompt: str, user_prompt: str, comm_id: int, use_pro=False) -> tuple[str, int, int, str]:
    if not gemini_manager: return "", 0, 0, "NO_KEYS"
    
    # Sử dụng bản 1.5 để tránh lỗi 403 Permission Denied
    models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite"]
    banned_models = set()
    
    while True:
        best_model = None
        client = None
        active_key = None
        min_wait = float('inf')
        
        # Chiến lược Tịnh tiến cho Gemini
        for model_id in models_to_try:
            if model_id in banned_models: continue
            
            c, k, w = await gemini_manager.get_client(model_id)
            if c is not None:
                best_model = model_id
                client = c
                active_key = k
                break
            if w < min_wait: min_wait = w
                
        if client is None:
            # Lập tức thoát để nhường cho tầng khác thay vì kẹt chờ
            log_action(comm_id, "SKIPPED", "GEMINI", "Toàn bộ", error=f"Hết Quota, chuyển tầng khác (Lock {min_wait:.1f}s)")
            break
            
        model_id = best_model
        log_action(comm_id, "TRYING", "GEMINI", model_id)
        
        # Đã giảm max_output_tokens xuống 1024
        config = genai_types.GenerateContentConfig(system_instruction=system_prompt, temperature=0.1, max_output_tokens=1024)
        
        try:
            response = await client.aio.models.generate_content(model=model_id, contents=user_prompt, config=config)
            
            # Ép key nghỉ 4.5s sau mỗi request (Gemini Free tier giới hạn 15 RPM ~ 4s/req)
            await gemini_manager.report_rate_limit(active_key, model_id, 0.0, global_delay=4.5)
            
            in_tok = response.usage_metadata.prompt_token_count if response.usage_metadata else 0
            out_tok = response.usage_metadata.candidates_token_count if response.usage_metadata else 0
            
            log_action(comm_id, "SUCCESS", "GEMINI", model_id, in_tok, out_tok)
            return response.text, in_tok, out_tok, "SUCCESS"
            
        except Exception as e:
            error_str = str(e)
            
            # Nếu là lỗi 429 hoặc 500/503 (Server bận)
            if "429" in error_str or "503" in error_str or "500" in error_str or "Quota" in error_str:
                await gemini_manager.report_rate_limit(active_key, model_id, 60.0)
                log_action(comm_id, "RATE_LIMIT", "GEMINI", model_id, error=f"Khóa Key {active_key[:8]} 60s")
                continue 
            
            # Các lỗi khác như 403, 400 thì cấm model này
            log_action(comm_id, "FAILED", "GEMINI", model_id, error=error_str[:50])
            banned_models.add(model_id)
            continue
            
    return "", 0, 0, "QUOTA_EXHAUSTED"

github_client = AsyncOpenAI(base_url="https://models.inference.ai.azure.com", api_key=GITHUB_TOKEN) if GITHUB_TOKEN else None

async def call_github(system_prompt: str, user_prompt: str, comm_id: int) -> tuple[str, int, int, str]:
    if not github_client: return "", 0, 0, "NO_TOKEN"
    models = [ "Meta-Llama-3.1-8B-Instruct", "gpt-4o-mini", "gpt-4o", "Meta-Llama-3.1-405B-Instruct"]
    
    for model_id in models:
        log_action(comm_id, "TRYING", "GITHUB", model_id)
        try:
            response = await github_client.chat.completions.create(
                model=model_id, messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.1, max_tokens=1024,
                response_format={"type": "json_object"}
            )
            in_tok = response.usage.prompt_tokens
            out_tok = response.usage.completion_tokens
            log_action(comm_id, "SUCCESS", "GITHUB", model_id, in_tok, out_tok)
            return response.choices[0].message.content, in_tok, out_tok, "SUCCESS"
        except Exception as e:
            error_str = str(e)
            log_action(comm_id, "FAILED", "GITHUB", model_id, error=error_str[:50])
            if "401" in error_str:
                log_action(comm_id, "SKIPPED", "GITHUB", "Toàn bộ", error="Token GitHub không hợp lệ (401)")
                break # Dừng ngay toàn bộ tầng GitHub
            if "429" not in error_str: 
                break
                
    return "", 0, 0, "GITHUB_FAILED"

# ====================================================================
# TẦNG 4: HUGGING FACE (Vắt kiệt Serverless API)
# ====================================================================
hf_client = AsyncOpenAI(
    base_url="https://api-inference.huggingface.co/v1/",
    api_key=HF_TOKEN
) if HF_TOKEN else None

# ====================================================================
# TẦNG 4: HUGGING FACE (Sử dụng AsyncInferenceClient chính chủ)
# ====================================================================
# Khởi tạo Client nếu có Token. Tham số timeout=120 giúp nó kiên nhẫn hơn với các model đang tải (Cold Start).
hf_client = AsyncInferenceClient(
    token=HF_TOKEN,
    timeout=120.0 
) if HF_TOKEN else None

async def call_hf(system_prompt: str, user_prompt: str, comm_id: int) -> tuple[str, int, int, str]:
    if not hf_client: return "", 0, 0, "NO_TOKEN"
    
    # Ưu tiên model DeepSeek để có khả năng suy luận tốt, sau đó là Llama và Qwen
    models = [
        "meta-llama/Llama-3.1-8B-Instruct",
        "Qwen/Qwen2.5-7B-Instruct",
        "Qwen/Qwen2.5-72B-Instruct",
        "meta-llama/Llama-3.1-70B-Instruct",
        "deepseek-ai/DeepSeek-R1-Distill-Llama-8B",
    ]
    
    for model_id in models:
        log_action(comm_id, "TRYING", "HF", model_id)
        try:
            # Sử dụng cú pháp chat_completion chuẩn của Hugging Face
            response = await hf_client.chat_completion(
                model=model_id,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.1, 
                max_tokens=1024
            )
            
            # InferenceClient tự động chuẩn hóa usage thành object (nếu có)
            in_tok = response.usage.prompt_tokens if hasattr(response, 'usage') and response.usage else 0
            out_tok = response.usage.completion_tokens if hasattr(response, 'usage') and response.usage else 0
            
            # Lấy nội dung text
            content = response.choices[0].message.content
            
            log_action(comm_id, "SUCCESS", "HF", model_id, in_tok, out_tok)
            return content, in_tok, out_tok, "SUCCESS"
            
        # TÌM ĐOẠN XỬ LÝ LỖI TRONG call_hf VÀ THAY THẾ BẰNG:
        except Exception as e:
            error_str = str(e)
            # Lấy dòng đầu tiên của chuỗi lỗi và in ra 150 ký tự để không bị che khuất mã lỗi HTTP
            short_error = error_str.split('\n')[0][:150] 
            log_action(comm_id, "FAILED", "HF", model_id, error=short_error)
            
            if "401" in error_str or "unauthorized" in error_str.lower():
                log_action(comm_id, "SKIPPED", "HF", "Toàn bộ", error="Token Hugging Face không hợp lệ (401)")
                break 
                
            continue
            
    return "", 0, 0, "HF_FAILED"

# ====================================================================
# TẦNG 5: SAMBANOVA (Sử dụng AsyncOpenAI)
# ====================================================================
sambanova_client = AsyncOpenAI(
    base_url="https://api.sambanova.ai/v1",
    api_key=SAMBANOVA_TOKEN
) if SAMBANOVA_TOKEN else None

async def call_sambanova(system_prompt: str, user_prompt: str, comm_id: int) -> tuple[str, int, int, str]:
    if not sambanova_client: return "", 0, 0, "NO_TOKEN"
    
    models = [
        "Llama-4-Maverick-17B-128E-Instruct",
        "Meta-Llama-3.3-70B-Instruct",
        "gemma-3-12b-it",
        "gemma-4-31B-it",
        "gpt-oss-120b",
        "DeepSeek-V3.1",
        "DeepSeek-V3.2",
    ]
    
    for model_id in models:
        log_action(comm_id, "TRYING", "SAMBA", model_id)
        try:
            response = await sambanova_client.chat.completions.create(
                model=model_id,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.1,
                max_tokens=1024
            )
            
            in_tok = response.usage.prompt_tokens if response.usage else 0
            out_tok = response.usage.completion_tokens if response.usage else 0
            
            content = response.choices[0].message.content
            
            log_action(comm_id, "SUCCESS", "SAMBA", model_id, in_tok, out_tok)
            return content, in_tok, out_tok, "SUCCESS"
            
        except Exception as e:
            error_str = str(e)
            short_error = error_str.split('\n')[0][:150]
            log_action(comm_id, "FAILED", "SAMBA", model_id, error=short_error)
            
            if "401" in error_str or "unauthorized" in error_str.lower():
                log_action(comm_id, "SKIPPED", "SAMBA", "Toàn bộ", error="Token SambaNova không hợp lệ (401)")
                break # Dừng tầng SambaNova nếu sai token
            
            continue
            
    return "", 0, 0, "SAMBANOVA_FAILED"

# ====================================================================
# TẦNG 6: CEREBRAS (Sử dụng AsyncOpenAI)
# ====================================================================
cerebras_client = AsyncOpenAI(
    base_url="https://api.cerebras.ai/v1",
    api_key=CEREBRAS_TOKEN
) if CEREBRAS_TOKEN else None

async def call_cerebras(system_prompt: str, user_prompt: str, comm_id: int) -> tuple[str, int, int, str]:
    if not cerebras_client: return "", 0, 0, "NO_TOKEN"
    
    models = [
        "gpt-oss-120b",
        "zai-glm-4.7",
    ]
    
    for model_id in models:
        log_action(comm_id, "TRYING", "CEREBRAS", model_id)
        try:
            response = await cerebras_client.chat.completions.create(
                model=model_id,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.1, 
                max_tokens=1024
            )
            
            in_tok = response.usage.prompt_tokens if response.usage else 0
            out_tok = response.usage.completion_tokens if response.usage else 0
            
            content = response.choices[0].message.content
            
            log_action(comm_id, "SUCCESS", "CEREBRAS", model_id, in_tok, out_tok)
            return content, in_tok, out_tok, "SUCCESS"
            
        except Exception as e:
            error_str = str(e)
            short_error = error_str.split('\n')[0][:150]
            log_action(comm_id, "FAILED", "CEREBRAS", model_id, error=short_error)
            
            if "401" in error_str or "unauthorized" in error_str.lower():
                log_action(comm_id, "SKIPPED", "CEREBRAS", "Toàn bộ", error="Token Cerebras không hợp lệ (401)")
                break
                
            continue
            
    return "", 0, 0, "CEREBRAS_FAILED"