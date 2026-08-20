"""
Tóm tắt trường descriptions cho nodes/edges (fuzzy matched).
- Xử lý tuần tự, xoay vòng (key, model) theo từng lần gọi LLM.
- Checkpoint theo id từng bản ghi; lưu output định kỳ.
- Output: descriptions là string (không còn list sau khi xử lý).
"""

import asyncio
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import tiktoken
from dotenv import dotenv_values
from google import genai
from google.genai import types as genai_types
from groq import AsyncGroq
from huggingface_hub import AsyncInferenceClient
from openai import AsyncOpenAI

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
INPUT_NODES = r"C:\1. Project\ĐATN\Data\07_Entities_matching\3_fuzzy_out\fuzzy_matched_nodes.json"
INPUT_EDGES = r"C:\1. Project\ĐATN\Data\07_Entities_matching\3_fuzzy_out\fuzzy_matched_edges.json"
OUTPUT_DIR = r"C:\1. Project\ĐATN\Data\07_Entities_matching\6_graph_final"
OUTPUT_NODES = os.path.join(OUTPUT_DIR, "nodes.json")
OUTPUT_EDGES = os.path.join(OUTPUT_DIR, "edges.json")
PROGRESS_DIR = os.path.join(OUTPUT_DIR, ".summarize_progress")
STATE_FILE = os.path.join(PROGRESS_DIR, "state.json")
FAILED_LOG_FILE = os.path.join(PROGRESS_DIR, "failed_summaries.txt")

SAVE_EVERY = 25
MAX_INPUT_TOKENS = 4000
MAX_OUTPUT_TOKENS = 2048
TOKEN_BOOST_INPUT_STEP = 1500
TOKEN_BOOST_OUTPUT_STEP = 512
MAX_INPUT_TOKENS_CAP = 12000
MAX_OUTPUT_TOKENS_CAP = 4096

# ---------------------------------------------------------------------------
# LLM credentials (độc lập để router tuyến tính không phụ thuộc cascade song song)
# ---------------------------------------------------------------------------
_env = dotenv_values(r"C:\1. Project\ĐATN\.env")
GROQ_KEYS = [v for k, v in _env.items() if k.startswith("GROQ_API_KEY") and v.strip()]
GEMINI_KEYS = [v for k, v in _env.items() if k.startswith("GEMINI_API_KEY") and v.strip()]
GITHUB_TOKEN = _env.get("GITHUB_TOKEN", "").strip()
HF_TOKEN = _env.get("HF_TOKEN", "").strip()
SAMBANOVA_API_KEY = _env.get("SAMBANOVA_API_KEY", "").strip()
CEREBRAS_API_KEY = _env.get("CEREBRAS_API_KEY", "").strip()

GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "openai/gpt-oss-20b",
    "qwen/qwen3-32b",
    "llama-3.1-8b-instant",
]
GITHUB_MODELS = [
    "Meta-Llama-3.1-8B-Instruct",
    "gpt-4o-mini",
    "gpt-4o", 
    "Meta-Llama-3.1-405B-Instruct"
]
GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite"]
HF_MODELS = [
    "meta-llama/Llama-3.1-8B-Instruct",
    "Qwen/Qwen2.5-7B-Instruct",
    "Qwen/Qwen2.5-72B-Instruct",
    "meta-llama/Llama-3.1-70B-Instruct",
    "deepseek-ai/DeepSeek-R1-Distill-Llama-8B",
]
SAMBANOVA_MODELS = [
    "DeepSeek-V3.1",
    "DeepSeek-V3.2",
    "Llama-4-Maverick-17B-128E-Instruct",
    "Meta-Llama-3.3-70B-Instruct",
    "gemma-3-12b-it",
    "gemma-4-31B-it",
    "gpt-oss-120b",
]
CEREBRAS_MODELS = [
    "gpt-oss-120b",
    "zai-glm-4.7",
]
# Free tier ~5 req/phút → nghỉ giữa các request Cerebras
CEREBRAS_REQUEST_DELAY_SEC = 13.0

_groq_clients: dict[int, AsyncGroq] = {}
_gemini_clients: dict[int, genai.Client] = {}
_github_client: Optional[AsyncOpenAI] = None
_hf_client: Optional[AsyncInferenceClient] = None
_sambanova_client: Optional[AsyncOpenAI] = None
_cerebras_client: Optional[AsyncOpenAI] = None

if GITHUB_TOKEN:
    _github_client = AsyncOpenAI(
        base_url="https://models.inference.ai.azure.com", api_key=GITHUB_TOKEN
    )
if HF_TOKEN:
    _hf_client = AsyncInferenceClient(token=HF_TOKEN, timeout=120.0)
if SAMBANOVA_API_KEY:
    _sambanova_client = AsyncOpenAI(
        base_url="https://api.sambanova.ai/v1",
        api_key=SAMBANOVA_API_KEY,
    )
if CEREBRAS_API_KEY:
    _cerebras_client = AsyncOpenAI(
        base_url="https://api.cerebras.ai/v1",
        api_key=CEREBRAS_API_KEY,
    )

# ---------------------------------------------------------------------------
# Prompt & token utils
# ---------------------------------------------------------------------------
SUMMARIZE_PROMPT_VI = """
Bạn là một trợ lý AI hữu ích chịu trách nhiệm tạo ra một bản tóm tắt toàn diện cho các dữ liệu được cung cấp dưới đây.
Dưới đây là một hoặc hai thực thể (entities), cùng với một danh sách các mô tả ban đầu, tất cả đều liên quan đến cùng một thực thể hoặc nhóm thực thể này.
Hãy tổng hợp và hợp nhất tất cả các mô tả này thành một bản mô tả chi tiết và duy nhất. 
Hãy đảm bảo bao gồm các thông tin quan trọng được thu thập từ tất cả các mô tả ban đầu.
Nếu các mô tả được cung cấp có thông tin mâu thuẫn, hãy giải quyết các mâu thuẫn đó và cung cấp một bản tóm tắt nhất quán, hợp lý.
Đảm bảo bản tóm tắt được viết ở ngôi thứ ba, và bao gồm đầy đủ tên của các thực thể để người đọc nắm được ngữ cảnh.

# Quy tắc BẮT BUỘC:
- CHỈ SỬ DỤNG thông tin từ danh sách mô tả được cung cấp. TUYỆT ĐỐI KHÔNG tự sáng tạo (hallucinate), bịa đặt hoặc thêm bất kỳ kiến thức nào nằm ngoài dữ liệu gốc.
- Nếu thông tin quá lộn xộn hoặc ít, hãy chỉ giữ đúng nội dung có sẵn, không tự kéo dài thêm câu chữ.
- Trả về trực tiếp duy nhất đoạn văn bản đã tóm tắt.
- TUYỆT ĐỐI KHÔNG thêm các câu mào đầu, bình luận, markdown (như ```) hay json format.

#######
-Dữ liệu-
Thực thể: {entity_name}
Danh sách mô tả:
{description_list}
#######
Output:
"""

tokenizer = tiktoken.get_encoding("cl100k_base")
_THINKING_TAG_RE = re.compile(
    r"<think>[\s\S]*?</think>", re.IGNORECASE
)
_THINKING_OPEN_RE = re.compile(r"<think>[\s\S]*", re.IGNORECASE)
SYSTEM_PROMPT = (
    "Bạn là trợ lý y khoa chuyên nghiệp và làm theo đúng định dạng được hướng dẫn. "
    "Tuyệt đối không hallucinate."
)


def count_tokens(text: str) -> int:
    return len(tokenizer.encode(str(text)))


def strip_thinking_tags(text: str) -> str:
    if not text:
        return ""
    cleaned = _THINKING_TAG_RE.sub("", str(text))
    cleaned = _THINKING_OPEN_RE.sub("", cleaned)
    return cleaned.strip()


def contains_thinking_tags(text: str) -> bool:
    return bool(text) and "<think>" in str(text).lower()


def format_log_item_id(kind: str, record_id: Any, label: str = "") -> str:
    label = (label or "")[:36]
    return f"{kind}|id={record_id}|{label}"


def log_summarize_event(item_id: str, event: str, detail: str = ""):
    time_str = time.strftime("%H:%M:%S")
    msg = f"[{time_str}] | {item_id:<48} | SUMMARY  | {event:<10}"
    if detail:
        msg += f" | {detail}"
    print(msg)


def log_llm(item_id: str, action: str, provider: str, model: str, **kwargs):
    time_str = time.strftime("%H:%M:%S")
    msg = f"[{time_str}] | {item_id:<48} | {provider:<7} | {model:<25} | {action:<10}"
    if kwargs.get("in_tok") is not None:
        msg += f" | In: {kwargs['in_tok']:<5} | Out: {kwargs.get('out_tok', 0):<4}"
    if kwargs.get("error"):
        msg += f" | Lỗi: {kwargs['error']}"
    print(msg)


def clean_llm_output(text: str) -> str:
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text.strip())
    text = re.sub(r"\n?```$", "", text)
    text = text.replace("```", "")
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict) and len(parsed) > 0:
            first_val = list(parsed.values())[0]
            if isinstance(first_val, str):
                text = first_val
    except json.JSONDecodeError:
        pass
    text = re.sub(r'^\{\s*"[^"]+"\s*:\s*"', "", text.strip())
    text = re.sub(r'"\s*\}$', "", text.strip())
    lines = text.strip().split("\n")
    if lines:
        first_line = lines[0].lower()
        if any(
            kw in first_line
            for kw in [
                "dưới đây là",
                "đây là",
                "tóm tắt",
                "output:",
                "bản tóm tắt",
                "dựa trên các mô tả",
            ]
        ):
            if ":" in lines[0] or len(lines[0]) < 50:
                lines = lines[1:]
    return strip_thinking_tags("\n".join(lines))


def is_refusal(text: str) -> bool:
    lower_txt = text.lower()
    if "xin lỗi" in lower_txt and "không thể" in lower_txt:
        return True
    if "as an ai" in lower_txt or "i cannot fulfill" in lower_txt:
        return True
    if "tôi không thể" in lower_txt and "y tế" in lower_txt:
        return True
    return False


_SENTENCE_END_RE = re.compile(r'[.!?…\)"»\'"]\s*$')
_TRUNCATED_TAIL_RE = re.compile(
    r"(?:[-*•]\s+\S+|:|\(|,\s*|\b(và|hoặc|như|ví dụ|bao gồm)\s*)$",
    re.IGNORECASE,
)


def is_output_truncated(
    text: str,
    finish_reason: Optional[str] = None,
    out_tokens: int = 0,
    max_output_tokens: int = MAX_OUTPUT_TOKENS,
) -> bool:
    """Phát hiện câu trả lời bị cắt (finish_reason=length hoặc heuristic)."""
    if finish_reason in ("length", "max_tokens", "MAX_TOKENS"):
        return True
    cleaned = (text or "").strip()
    if not cleaned:
        return False
    if out_tokens >= max(64, int(max_output_tokens * 0.92)):
        if not _SENTENCE_END_RE.search(cleaned):
            return True
    if len(cleaned) < 60:
        return False
    if _SENTENCE_END_RE.search(cleaned):
        return False
    last_line = cleaned.split("\n")[-1].strip()
    if _TRUNCATED_TAIL_RE.search(last_line):
        return True
    if cleaned.count("(") > cleaned.count(")"):
        return True
    if len(last_line) > 180 and not _SENTENCE_END_RE.search(last_line):
        return True
    return False


def _truncated_key(kind: str) -> str:
    return "nodes_truncated" if kind == "NODE" else "edges_truncated"


def get_truncation_boost(state: dict, kind: str, record_id: Any) -> int:
    entry = state.get(_truncated_key(kind), {}).get(str(record_id), 0)
    if isinstance(entry, dict):
        return int(entry.get("boost_level", 0))
    return int(entry) if entry else 0


def mark_truncated(state: dict, kind: str, record_id: Any):
    key = _truncated_key(kind)
    state.setdefault(key, {})
    sid = str(record_id)
    prev = get_truncation_boost(state, kind, record_id)
    state[key][sid] = {"boost_level": prev + 1}
    done_key = "nodes_done" if kind == "NODE" else "edges_done"
    if sid in state.get(done_key, []):
        state[done_key] = [x for x in state[done_key] if x != sid]


def clear_truncated(state: dict, kind: str, record_id: Any):
    key = _truncated_key(kind)
    state.get(key, {}).pop(str(record_id), None)


def is_marked_truncated(state: dict, kind: str, record_id: Any) -> bool:
    return str(record_id) in state.get(_truncated_key(kind), {})


def token_limits_for_record(state: dict, kind: str, record_id: Any) -> tuple[int, int]:
    """Input/output token limits; tăng theo boost_level trong state."""
    boost = get_truncation_boost(state, kind, record_id)
    max_in = min(
        MAX_INPUT_TOKENS_CAP,
        MAX_INPUT_TOKENS + boost * TOKEN_BOOST_INPUT_STEP,
    )
    max_out = min(
        MAX_OUTPUT_TOKENS_CAP,
        MAX_OUTPUT_TOKENS + boost * TOKEN_BOOST_OUTPUT_STEP,
    )
    return max_in, max_out


def prepare_prompt(entity_name: str, descriptions: list, max_input_tokens: int = MAX_INPUT_TOKENS) -> str:
    base_len = count_tokens(
        SUMMARIZE_PROMPT_VI.format(entity_name=entity_name, description_list="")
    )
    budget = max_input_tokens - base_len
    selected_desc = []
    current_tokens = 0
    for i, desc in enumerate(descriptions):
        desc_line = f"- {str(desc)}"
        desc_tokens = count_tokens(desc_line)
        if current_tokens + desc_tokens > budget:
            selected_desc.append(
                f"... (Đã lược bỏ {len(descriptions) - i} mô tả phía sau do giới hạn độ dài) ..."
            )
            break
        selected_desc.append(desc_line)
        current_tokens += desc_tokens
    return SUMMARIZE_PROMPT_VI.format(
        entity_name=entity_name, description_list="\n".join(selected_desc)
    )


def unique_descriptions(descriptions: list) -> list[str]:
    return list(
        dict.fromkeys(
            [
                strip_thinking_tags(str(d).strip())
                for d in descriptions
                if strip_thinking_tags(str(d).strip())
            ]
        )
    )


def descriptions_need_llm(descriptions: Any) -> bool:
    if isinstance(descriptions, str):
        return False
    if not isinstance(descriptions, list):
        return False
    return len(unique_descriptions(descriptions)) > 1


def collapse_without_llm(descriptions: Any) -> str:
    if isinstance(descriptions, str):
        return strip_thinking_tags(descriptions)
    if not isinstance(descriptions, list) or len(descriptions) == 0:
        return ""
    unique = unique_descriptions(descriptions)
    return unique[0] if unique else ""


# ---------------------------------------------------------------------------
# Linear LLM router: xoay vòng (provider, key_index, model)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class LLMSlot:
    provider: str
    model: str
    key_index: Optional[int] = None


def build_llm_slots() -> list[LLMSlot]:
    slots: list[LLMSlot] = []
    for ki in range(len(GROQ_KEYS)):
        for model in GROQ_MODELS:
            slots.append(LLMSlot("groq", model, ki))
    for model in GITHUB_MODELS:
        slots.append(LLMSlot("github", model, None))
    for ki in range(len(GEMINI_KEYS)):
        for model in GEMINI_MODELS:
            slots.append(LLMSlot("gemini", model, ki))
    for model in HF_MODELS:
        slots.append(LLMSlot("hf", model, None))
    for model in SAMBANOVA_MODELS:
        slots.append(LLMSlot("sambanova", model, None))
    for model in CEREBRAS_MODELS:
        slots.append(LLMSlot("cerebras", model, None))
    return slots


class LinearLLMRouter:
    def __init__(self, start_index: int = 0):
        self.slots = build_llm_slots()
        self.index = start_index % max(len(self.slots), 1)

    def current(self) -> LLMSlot:
        return self.slots[self.index]

    def advance(self):
        if self.slots:
            self.index = (self.index + 1) % len(self.slots)


def _groq_client(key_index: int) -> AsyncGroq:
    if key_index not in _groq_clients:
        _groq_clients[key_index] = AsyncGroq(
            api_key=GROQ_KEYS[key_index], max_retries=0
        )
    return _groq_clients[key_index]


def _gemini_client(key_index: int) -> genai.Client:
    if key_index not in _gemini_clients:
        _gemini_clients[key_index] = genai.Client(api_key=GEMINI_KEYS[key_index])
    return _gemini_clients[key_index]


async def invoke_slot(
    slot: LLMSlot,
    system_prompt: str,
    user_prompt: str,
    item_id: str,
    max_output_tokens: int = MAX_OUTPUT_TOKENS,
) -> tuple[str, str, Optional[str]]:
    """Trả về (content, status, finish_reason). status: SUCCESS | RATE_LIMIT | FAILED | NO_KEYS."""
    try:
        if slot.provider == "groq":
            if not GROQ_KEYS or slot.key_index is None:
                return "", "NO_KEYS", None
            client = _groq_client(slot.key_index)
            log_llm(item_id, "TRYING", "GROQ", slot.model)
            raw = await client.chat.completions.with_raw_response.create(
                model=slot.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=max_output_tokens,
                top_p=0.9,
            )
            parsed = await raw.parse()
            choice = parsed.choices[0]
            content = choice.message.content or ""
            finish = getattr(choice, "finish_reason", None)
            in_tok = parsed.usage.prompt_tokens if parsed.usage else 0
            out_tok = parsed.usage.completion_tokens if parsed.usage else 0
            log_llm(item_id, "SUCCESS", "GROQ", slot.model, in_tok=in_tok, out_tok=out_tok)
            await asyncio.sleep(3.0)
            return content, "SUCCESS", finish

        if slot.provider == "github":
            if not _github_client:
                return "", "NO_KEYS", None
            log_llm(item_id, "TRYING", "GITHUB", slot.model)
            response = await _github_client.chat.completions.create(
                model=slot.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=max_output_tokens,
            )
            choice = response.choices[0]
            in_tok = response.usage.prompt_tokens if response.usage else 0
            out_tok = response.usage.completion_tokens if response.usage else 0
            log_llm(item_id, "SUCCESS", "GITHUB", slot.model, in_tok=in_tok, out_tok=out_tok)
            return choice.message.content or "", "SUCCESS", choice.finish_reason

        if slot.provider == "gemini":
            if not GEMINI_KEYS or slot.key_index is None:
                return "", "NO_KEYS", None
            client = _gemini_client(slot.key_index)
            log_llm(item_id, "TRYING", "GEMINI", slot.model)
            config = genai_types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.1,
                max_output_tokens=max_output_tokens,
            )
            response = await client.aio.models.generate_content(
                model=slot.model, contents=user_prompt, config=config
            )
            in_tok = (
                response.usage_metadata.prompt_token_count
                if response.usage_metadata
                else 0
            )
            out_tok = (
                response.usage_metadata.candidates_token_count
                if response.usage_metadata
                else 0
            )
            finish = None
            if response.candidates:
                finish = getattr(response.candidates[0], "finish_reason", None)
            log_llm(item_id, "SUCCESS", "GEMINI", slot.model, in_tok=in_tok, out_tok=out_tok)
            await asyncio.sleep(4.5)
            return response.text or "", "SUCCESS", finish

        if slot.provider == "hf":
            if not _hf_client:
                return "", "NO_KEYS", None
            log_llm(item_id, "TRYING", "HF", slot.model)
            response = await _hf_client.chat_completion(
                model=slot.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=max_output_tokens,
            )
            choice = response.choices[0]
            in_tok = (
                response.usage.prompt_tokens
                if hasattr(response, "usage") and response.usage
                else 0
            )
            out_tok = (
                response.usage.completion_tokens
                if hasattr(response, "usage") and response.usage
                else 0
            )
            finish = getattr(choice, "finish_reason", None)
            log_llm(item_id, "SUCCESS", "HF", slot.model, in_tok=in_tok, out_tok=out_tok)
            return choice.message.content or "", "SUCCESS", finish

        if slot.provider == "sambanova":
            if not _sambanova_client:
                return "", "NO_KEYS", None
            log_llm(item_id, "TRYING", "SAMBNOVA", slot.model)
            response = await _sambanova_client.chat.completions.create(
                model=slot.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=max_output_tokens,
            )
            choice = response.choices[0]
            in_tok = response.usage.prompt_tokens if response.usage else 0
            out_tok = response.usage.completion_tokens if response.usage else 0
            log_llm(
                item_id, "SUCCESS", "SAMBNOVA", slot.model, in_tok=in_tok, out_tok=out_tok
            )
            await asyncio.sleep(2.0)
            return choice.message.content or "", "SUCCESS", choice.finish_reason

        if slot.provider == "cerebras":
            if not _cerebras_client:
                return "", "NO_KEYS", None
            log_llm(item_id, "TRYING", "CEREBRAS", slot.model)
            response = await _cerebras_client.chat.completions.create(
                model=slot.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=max_output_tokens,
            )
            choice = response.choices[0]
            in_tok = response.usage.prompt_tokens if response.usage else 0
            out_tok = response.usage.completion_tokens if response.usage else 0
            log_llm(
                item_id, "SUCCESS", "CEREBRAS", slot.model, in_tok=in_tok, out_tok=out_tok
            )
            await asyncio.sleep(CEREBRAS_REQUEST_DELAY_SEC)
            return choice.message.content or "", "SUCCESS", choice.finish_reason

    except Exception as e:
        err = str(e)
        short = err.split("\n")[0][:120]
        if any(x in err for x in ("429", "rate_limit", "tpm", "Quota")):
            log_llm(item_id, "RATE_LIMIT", slot.provider.upper(), slot.model, error=short)
            return "", "RATE_LIMIT", None
        if "413" in err or "too large" in err.lower():
            log_llm(item_id, "FAILED", slot.provider.upper(), slot.model, error="413 context")
            return "", "FAILED", None
        log_llm(item_id, "ERROR", slot.provider.upper(), slot.model, error=short)
        return "", "FAILED", None

    return "", "FAILED", None


class SummarizeOutcome:
    __slots__ = ("text", "truncated")

    def __init__(self, text: Optional[str] = None, truncated: bool = False):
        self.text = text
        self.truncated = truncated


async def attempt_summarize(
    entity_name: str,
    descriptions: list,
    item_id: str,
    router: LinearLLMRouter,
    max_input_tokens: int = MAX_INPUT_TOKENS,
    max_output_tokens: int = MAX_OUTPUT_TOKENS,
) -> SummarizeOutcome:
    unique_desc = unique_descriptions(descriptions)
    if len(unique_desc) == 0:
        return SummarizeOutcome("")
    if len(unique_desc) == 1:
        return SummarizeOutcome(unique_desc[0])

    user_prompt = prepare_prompt(
        entity_name, unique_desc, max_input_tokens=max_input_tokens
    )

    if not router.slots:
        print("[!] Không có API key/model nào. Kiểm tra file .env")
        return SummarizeOutcome(None, truncated=False)

    while True:
        tried = 0
        n = len(router.slots)
        while tried < n:
            slot = router.slots[(router.index + tried) % n]
            result, status, finish_reason = await invoke_slot(
                slot,
                SYSTEM_PROMPT,
                user_prompt,
                item_id,
                max_output_tokens=max_output_tokens,
            )

            if status == "SUCCESS" and result and result.strip():
                clean_res = clean_llm_output(result)
                out_tok = count_tokens(clean_res)
                if clean_res and not is_refusal(clean_res) and not contains_thinking_tags(
                    clean_res
                ):
                    if is_output_truncated(
                        clean_res, finish_reason, out_tok, max_output_tokens
                    ):
                        log_summarize_event(
                            item_id,
                            "TRUNCATED",
                            f"finish={finish_reason} | in={max_input_tokens} out={max_output_tokens}",
                        )
                        return SummarizeOutcome(None, truncated=True)
                    router.index = (router.index + tried + 1) % n
                    return SummarizeOutcome(clean_res)
                if clean_res and contains_thinking_tags(clean_res):
                    log_summarize_event(
                        item_id, "RETRY", "Output còn <think>, slot tiếp theo"
                    )

            tried += 1

        log_summarize_event(
            item_id, "WAIT", "Hết vòng slot, ngủ 60s (quota/rate limit)..."
        )
        await asyncio.sleep(60)


# ---------------------------------------------------------------------------
# Progress / checkpoint
# ---------------------------------------------------------------------------
def default_state() -> dict:
    return {
        "version": 2,
        "router_index": 0,
        "nodes_done": [],
        "edges_done": [],
        "nodes_truncated": {},
        "edges_truncated": {},
        "stats": {
            "nodes_llm": 0,
            "nodes_skip": 0,
            "nodes_failed": 0,
            "nodes_truncated": 0,
            "edges_llm": 0,
            "edges_skip": 0,
            "edges_failed": 0,
            "edges_truncated": 0,
        },
    }


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
        state.setdefault("nodes_done", [])
        state.setdefault("edges_done", [])
        state.setdefault("nodes_truncated", {})
        state.setdefault("edges_truncated", {})
        state.setdefault("stats", default_state()["stats"])
        state.setdefault("router_index", 0)
        return state
    return default_state()


def save_state(state: dict):
    os.makedirs(PROGRESS_DIR, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_json_array(path: str) -> list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json_array(path: str, data: list):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def merge_records(
    input_records: list,
    output_records: Optional[list],
    done_ids: set[str],
    truncated_ids: Optional[set[str]] = None,
) -> list[dict]:
    """Ưu tiên bản ghi output đã xử lý; giữ input nếu id đang chờ retry do cắt cụt."""
    truncated_ids = truncated_ids or set()
    by_id: dict[str, dict] = {str(r["id"]): dict(r) for r in input_records}
    if output_records:
        for r in output_records:
            rid = str(r["id"])
            if rid in truncated_ids:
                continue
            if rid in done_ids or isinstance(r.get("descriptions"), str):
                by_id[rid] = dict(r)
    return [by_id[str(r["id"])] for r in input_records]


def mark_done(state: dict, kind: str, record_id: Any):
    key = "nodes_done" if kind == "NODE" else "edges_done"
    sid = str(record_id)
    if sid not in state[key]:
        state[key].append(sid)


def is_done(state: dict, kind: str, record_id: Any) -> bool:
    if is_marked_truncated(state, kind, record_id):
        return False
    key = "nodes_done" if kind == "NODE" else "edges_done"
    return str(record_id) in set(state[key])


async def process_record(
    record: dict,
    kind: str,
    entity_name: str,
    router: LinearLLMRouter,
    state: dict,
) -> bool:
    """
    Trả về True nếu xử lý xong (kể cả skip), False nếu cần retry sau.
    Luôn ghi descriptions thành string khi thành công.
    """
    rid = record["id"]
    item_id = format_log_item_id(kind, rid, entity_name)
    desc = record.get("descriptions")

    if is_done(state, kind, rid) or isinstance(desc, str):
        if isinstance(desc, str) and contains_thinking_tags(desc):
            record["descriptions"] = strip_thinking_tags(desc)
            log_summarize_event(item_id, "CLEANED", "Gỡ <think> khỏi bản đã lưu")
        mark_done(state, kind, rid)
        return True

    if not descriptions_need_llm(desc):
        record["descriptions"] = collapse_without_llm(desc)
        stat_key = f"{kind.lower()}s_skip"
        state["stats"][stat_key] = state["stats"].get(stat_key, 0) + 1
        log_summarize_event(
            item_id,
            "SKIP",
            f"≤1 mô tả → string ({len(record['descriptions'])} ký tự)",
        )
        mark_done(state, kind, rid)
        return True

    if not isinstance(desc, list):
        record["descriptions"] = collapse_without_llm(desc)
        mark_done(state, kind, rid)
        return True

    max_in, max_out = token_limits_for_record(state, kind, rid)
    boost = get_truncation_boost(state, kind, rid)
    if boost > 0:
        log_summarize_event(
            item_id,
            "RETRY+",
            f"boost={boost} | max_in={max_in} max_out={max_out}",
        )
    log_summarize_event(item_id, "START", f"{len(desc)} mô tả | {entity_name[:40]}")
    outcome = await attempt_summarize(
        entity_name,
        desc,
        item_id,
        router,
        max_input_tokens=max_in,
        max_output_tokens=max_out,
    )

    if outcome.truncated:
        mark_truncated(state, kind, rid)
        stat_key = f"{'nodes' if kind == 'NODE' else 'edges'}_truncated"
        state["stats"][stat_key] = state["stats"].get(stat_key, 0) + 1
        log_summarize_event(
            item_id,
            "DEFERRED",
            f"Lưu state → boost={get_truncation_boost(state, kind, rid)} lần chạy sau",
        )
        return False

    if outcome.text is not None:
        record["descriptions"] = outcome.text
        clear_truncated(state, kind, rid)
        stat_key = f"{'nodes' if kind == 'NODE' else 'edges'}_llm"
        state["stats"][stat_key] = state["stats"].get(stat_key, 0) + 1
        log_summarize_event(item_id, "DONE", f"{len(outcome.text)} ký tự")
        mark_done(state, kind, rid)
        return True

    stat_key = f"{'nodes' if kind == 'NODE' else 'edges'}_failed"
    state["stats"][stat_key] = state["stats"].get(stat_key, 0) + 1
    log_summarize_event(item_id, "FAILED", "Không ghi vào done — sẽ retry lần sau")
    with open(FAILED_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{kind} | id={rid} | {entity_name}\n")
    return False


async def run_batch(
    kind: str,
    input_path: str,
    output_path: str,
    records: list[dict],
    router: LinearLLMRouter,
    state: dict,
    name_fn,
):
    done_set = set(state["nodes_done"] if kind == "NODE" else state["edges_done"])
    truncated_map = state.get(_truncated_key(kind), {})
    pending = [r for r in records if str(r["id"]) not in done_set]
    pending.sort(
        key=lambda r: (
            0 if str(r["id"]) in truncated_map else 1,
            int(r["id"]) if str(r.get("id", "")).isdigit() else str(r["id"]),
        )
    )
    total = len(records)
    trunc_count = len(truncated_map)
    print(
        f"\n=== {kind}: {len(pending)} pending / {total} total "
        f"({trunc_count} chờ retry do cắt cụt) ==="
    )

    processed_since_save = 0
    for i, record in enumerate(pending, 1):
        entity_name = name_fn(record)
        ok = await process_record(record, kind, entity_name, router, state)
        if ok:
            processed_since_save += 1

        if processed_since_save >= SAVE_EVERY or i == len(pending):
            save_state(state)
            save_json_array(output_path, records)
            processed_since_save = 0
            done_count = len(
                state["nodes_done"] if kind == "NODE" else state["edges_done"]
            )
            print(
                f"[*] Đã lưu {kind} → {output_path} "
                f"({done_count}/{total} hoàn tất, router_index={router.index})"
            )


async def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(PROGRESS_DIR, exist_ok=True)

    if not os.path.exists(INPUT_NODES) or not os.path.exists(INPUT_EDGES):
        print("Thiếu file input fuzzy_matched_nodes.json hoặc fuzzy_matched_edges.json")
        return

    state = load_state()
    router = LinearLLMRouter(state.get("router_index", 0))

    print("Đang đọc input...")
    input_nodes = load_json_array(INPUT_NODES)
    input_edges = load_json_array(INPUT_EDGES)

    output_nodes = (
        load_json_array(OUTPUT_NODES) if os.path.exists(OUTPUT_NODES) else None
    )
    output_edges = (
        load_json_array(OUTPUT_EDGES) if os.path.exists(OUTPUT_EDGES) else None
    )

    nodes_done = set(state["nodes_done"])
    edges_done = set(state["edges_done"])
    nodes_truncated = set(state.get("nodes_truncated", {}).keys())
    edges_truncated = set(state.get("edges_truncated", {}).keys())
    nodes = merge_records(input_nodes, output_nodes, nodes_done, nodes_truncated)
    edges = merge_records(input_edges, output_edges, edges_done, edges_truncated)

    print(f"Slots LLM (xoay vòng): {len(router.slots)}")
    print(f"Resume: {len(nodes_done)} nodes, {len(edges_done)} edges đã xong")
    print(
        f"Truncated retry: {len(nodes_truncated)} nodes, {len(edges_truncated)} edges "
        f"(tăng token mỗi lần: in+{TOKEN_BOOST_INPUT_STEP}, out+{TOKEN_BOOST_OUTPUT_STEP})"
    )
    print(f"Output: {OUTPUT_DIR}")

    try:
        await run_batch(
            "NODE",
            INPUT_NODES,
            OUTPUT_NODES,
            nodes,
            router,
            state,
            lambda r: r.get("entity_name", f"Node_{r.get('id')}"),
        )
        state["router_index"] = router.index
        save_state(state)

        await run_batch(
            "EDGE",
            INPUT_EDGES,
            OUTPUT_EDGES,
            edges,
            router,
            state,
            lambda r: f"{r.get('source', '')} -> {r.get('target', '')}",
        )
        state["router_index"] = router.index
        save_state(state)

        save_json_array(OUTPUT_NODES, nodes)
        save_json_array(OUTPUT_EDGES, edges)
        print("\nHOÀN TẤT!")

    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n[!] Ngắt — đang lưu progress...")
        state["router_index"] = router.index
        save_state(state)
        save_json_array(OUTPUT_NODES, nodes)
        save_json_array(OUTPUT_EDGES, edges)
    except Exception as e:
        print(f"\n[!] Lỗi: {e} — đang lưu progress...")
        state["router_index"] = router.index
        save_state(state)
        save_json_array(OUTPUT_NODES, nodes)
        save_json_array(OUTPUT_EDGES, edges)
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
