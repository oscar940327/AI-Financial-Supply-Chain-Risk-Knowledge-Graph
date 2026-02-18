# -*- coding: utf-8 -*-
import os 
import re
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# 讀取 API key
API_KEY = os.getenv("OPENAI_API_KEY")

if not API_KEY:
    raise ValueError("API key not found. Please set the OPENAI_API environment variable.")

# 初始化 OpenAI 客戶端
client = OpenAI(api_key=API_KEY)

# 設計 Prompt，定義 Schema
def get_extraction_prompt(news_text, ticker):
    # 共用的 Schema 定義
    schema_instruction = """
    Please strictly follow the Schema definition below:
    1. Entity Types: ["Company", "Product", "Event", "Risk", "Person", "Organization"]
    2. Relation Types: [
        "AFFECTS", "CAUSES", "DELAYS", "CANCELS", "INCREASES", "DECREASES", 
        "LAUNCHES", "PARTNERS_WITH", "COMPETES_WITH", "REGULATES", 
        "ANNOUNCES", "BENEFITS_FROM",
        "WARNS", "MISSES", "LOWERS", "WITHDRAWS", "SCALE_BACK", "INCURS",
        "REDUCES", "COMMENTS_ON", "REPORTS", "EXPANDS", "INVESTS_IN",
        "OWNS", "MANAGES", "DEVELOPS", "TESTIFIES_BEFORE", "HAMPERS"
    ]
    """

    system_instruction = f"""
    You are a professional supply chain risk analyst. Your task is to extract "entity-relation-entity" triples from financial news.
    {schema_instruction}
    
    **CRITICAL RULES:**
    1. **RELATION CONSTRAINT**: You MUST ONLY use the relation types listed above. Do NOT use verbs like "SURGED", "TUMBLED", "ROSE", etc.
    2. **TARGET ANCHORING**: Focus ONLY on entities and events that have a direct or indirect relationship with the target entity: {ticker}. Ignore completely unrelated background news (e.g., unrelated entertainment or geopolitical events unless they directly affect {ticker} or its sector).
    3. **NO PLACEHOLDERS (ANTI-HALLUCINATION)**: Extract the ACTUAL NAMES of entities from the text. NEVER output literal category labels such as "Event", "Company", "Product", "Risk", "Person", or "Entity1" as the head or tail. If a company announces a relocation, the tail should be the specific action (e.g., "Headquarters relocation to Miami"), NOT the word "Event".

    ### Output Format:
    Return a JSON Array with this EXACT structure (the examples below use concrete names, do not use abstract placeholders):
    [
      {{"head": "Federal Reserve", "relation": "AFFECTS", "tail": "Tech Stocks"}},
      {{"head": "Apple", "relation": "LAUNCHES", "tail": "Vision Pro"}}
    ]
    
    Use "head" and "tail" as keys. The output format must be a pure JSON Array, without any Markdown tags or additional text.
    """

    user_content = f"Please analyze the following news content and extract triples relevant to {ticker}:\n\n{news_text}"
    return system_instruction, user_content


# 呼叫 OpenAI API 進行抽取，增加 ticker 參數
def extract_info_from_gpt(text, ticker):
    # 獲取提示詞並傳入 ticker
    system_prompt, user_prompt = get_extraction_prompt(text, ticker)

    try:
        response = client.chat.completions.create(
            model="gpt-5.2", 
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0 
        )

        # 獲取回應的文字內容
        raw_text = response.choices[0].message.content.strip()
        json_str = raw_text

        # 嘗試移除 Markdown code block (```json ... ```)
        if "```json" in json_str:
            pattern = r"```json(.*?)```"
            match = re.search(pattern, json_str, re.DOTALL)
            if match:
                json_str = match.group(1).strip()
            elif "```" in json_str:
                pattern = r"```(.*?)```"
                match = re.search(pattern, json_str, re.DOTALL)
                if match:
                    json_str = match.group(1).strip()

        # 尋找 JSON Array
        try:
            start_idx = json_str.find('[')
            end_idx = json_str.rfind(']')
            if start_idx != -1 and end_idx != -1:
                json_str = json_str[start_idx : end_idx + 1]
        except:
            pass

        # 轉換成 JSON
        data = json.loads(json_str)
        return data, raw_text
    
    except Exception as e:
        print(f"GPT extraction error: {e}")
        return [], ""

def run_llm_extraction(input_file, ticker):
    print("Selected mode: zero_shot")
    
    input_file = os.path.normpath(input_file)

    if not os.path.exists(input_file):
        print(f"Input file not found: {input_file}")
        return None
    
    with open(input_file, "r", encoding="utf-8") as f:
        news_list = json.load(f)
    
    extracted_results = []
    print(f"Starting LLM data extraction, total {len(news_list)} news articles...")

    for i, news in enumerate(news_list):
        print(f"Processing ({i+1}/{len(news_list)}): {news['title'][:50]}...")
        full_text = "\n".join(news['content'])

        triples, _ = extract_info_from_gpt(full_text, ticker)

        if triples:
            print(f"   -> Extracted {len(triples)} triples.")
        else:
            print("   -> No triples extracted.")

        result_entry = {
            "news_id": news['news_id'],
            "title": news['title'],
            "publish_time": news['publish_time'],
            "extraction_mode": "zero_shot",
            "triples": triples
        }
        extracted_results.append(result_entry)

    # 取得 input_file 所在的資料夾當作輸出資料夾，這樣就不用寫死路徑
    output_dir = os.path.dirname(input_file)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 修改檔名為動態生成
    output_filename = f"{ticker.lower()}_triples_zero_shot.json"
    output_file = os.path.join(output_dir, output_filename)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(extracted_results, f, ensure_ascii=False, indent=2)

    print(f"\nProcessing completed!")
    print(f"Saved extracted triples to: {output_file}")
    
    # 回傳檔案路徑交給下一個模組
    return output_file

if __name__ == "__main__":
    # 單檔測試區塊
    user_ticker = input("Please enter the stock ticker (e.g., PLTR): ").strip().upper()
    
    if user_ticker:
        # 模擬從 01 接收到的檔案路徑
        current_dir = os.path.dirname(os.path.abspath(__file__))
        test_input_path = os.path.join(current_dir, "..", "output", f"{user_ticker.lower()}_data", f"{user_ticker.lower()}_news.json")
        
        print(f"Trying to read test file: {test_input_path}")
        result_path = run_llm_extraction(test_input_path, user_ticker)
        
        print(f"Test completed, file path ready to be passed to next module (03): {result_path}")
    else:
        print("No ticker entered, program terminated.")