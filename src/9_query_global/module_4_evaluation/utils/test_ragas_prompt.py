# test_ragas_prompt.py
from ragas.metrics import faithfulness, answer_relevance

def print_ragas_prompts():
    print("="*50)
    print("1. PROMPT TRÍCH XUẤT LUẬN ĐIỂM (CỦA FAITHFULNESS):")
    print("="*50)
    # RAGAS chia Faithfulness làm 2 bước, đây là bước 1
    print(faithfulness.long_form_answer_prompt.instruction)
    print("\n[Các ví dụ mẫu (Few-shots) họ đưa vào]:")
    for example in faithfulness.long_form_answer_prompt.examples:
        print(example)

    print("\n" + "="*50)
    print("2. PROMPT KIỂM TRA ĐỘ TRUNG THỰC (CỦA FAITHFULNESS):")
    print("="*50)
    # Đây là bước 2: Kiểm tra chéo
    print(faithfulness.nli_statements_message.instruction)
    
    print("\n" + "="*50)
    print("3. PROMPT ANSWER RELEVANCE:")
    print("="*50)
    print(answer_relevance.question_generation.instruction)

if __name__ == "__main__":
    print_ragas_prompts()