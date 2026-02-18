# -*- coding: utf-8 -*-
import os
import re
import json
import time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

VALID_RELATIONS = [
    "AFFECTS", "CAUSES", "DELAYS", "CANCELS", "INCREASES", "DECREASES", 
    "LAUNCHES", "PARTNERS_WITH", "COMPETES_WITH", "REGULATES", 
    "ANNOUNCES", "BENEFITS_FROM", "WARNS", "MISSES", "LOWERS", 
    "WITHDRAWS", "SCALE_BACK", "INCURS", "REDUCES", "COMMENTS_ON", 
    "REPORTS", "EXPANDS", "INVESTS_IN", "OWNS", "MANAGES", 
    "DEVELOPS", "TESTIFIES_BEFORE", "HAMPERS"
]

def print_step(message):
    print(f"\n{message}\n")

def load_json(filepath):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

# 呼叫 GPT 進行三元組驗證並直接返回完整修正後的三元組列表
def verify_and_fix_triples(news_text, draft_triples):
    triples_str = "\n".join([
        f"- ({t['head']}, {t['relation']}, {t['tail']})"
        for t in draft_triples
    ])

    valid_relations_str = ", ".join(VALID_RELATIONS)
    
    prompt = f"""
    You are a knowledge graph quality control expert. Please verify the following triples extracted from the news article.

    **News Article:**
    {news_text}

    **Extracted Triples:**
    {triples_str}

    **Valid Relation Types (Strict Schema):**
    [{valid_relations_str}]

    **Your Task:**
    For each triple, decide:
    1. **KEEP**: The triple is correct, supported by the article, AND the relation is in the Valid Relation Types list.
    2. **MODIFY**: 
       - The relation is semantically correct but NOT in the Valid List (e.g., "RATES" -> change to "REPORTS" or "COMMENTS_ON").
       - The relation is factually incorrect -> provide the corrected relation.
    3. **DELETE**: The triple is a hallucination (not mentioned in the article) -> remove it.

    **Output Format (JSON only, no explanation):**
    {{
        "verified_triples": [
            {{
                "head": "Entity A",
                "relation": "CORRECT_RELATION_FROM_LIST",
                "tail": "Entity B",
                "action": "KEEP", 
                "reason": "Supported by text"
            }},
            {{
                "head": "Entity C",
                "relation": "REPORTS", 
                "tail": "Entity D",
                "action": "MODIFY", 
                "reason": "Changed RATES to REPORTS to match schema"
            }}
        ]
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-5.2",
            messages=[
                {"role": "system", "content": "You are a knowledge graph verification expert. Output valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        
        content = response.choices[0].message.content.strip()
        
        # 【優化點】使用 Regex 進行強健的 JSON 提取，避免因前後廢話導致解析失敗
        json_str = content
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
        
        # 尋找 JSON Array/Object 的邊界 (雙重保險)
        try:
            start_idx = json_str.find('{')
            end_idx = json_str.rfind('}')
            if start_idx != -1 and end_idx != -1:
                json_str = json_str[start_idx : end_idx + 1]
        except:
            pass
        
        result = json.loads(json_str)
        return result.get("verified_triples", [])
        
    except Exception as e:
        print(f"Error during LLM verification: {e}")
        return None

def run_auto_verifier(draft_file, news_file, ticker):
    print(f"Starting auto verification for {ticker}...")

    draft_file = os.path.normpath(draft_file)
    news_file = os.path.normpath(news_file)

    draft_data = load_json(draft_file)
    news_data = load_json(news_file)

    if not draft_data or not news_data:
        print("Failed to load necessary data. Exiting.")
        return None

    # 建立 news_id 到新聞內容的映射
    news_map = {news["news_id"]: news for news in news_data}

    verified_results = []

    stats = {
        "total_triples_before": 0,
        "total_triples_after": 0,
        "kept": 0,
        "modified": 0,
        "deleted": 0
    }

    print(f"Verifying triples for {len(draft_data)} news articles...")

    for idx, draft in enumerate(draft_data):
        news_id = draft.get("news_id")
        print(f"Processing {idx + 1}/{len(draft_data)}: news_id={news_id}...")

        if news_id not in news_map:
            print(f"Warning: news_id {news_id} not found in news data. Skipping.")
            continue

        news = news_map[news_id]
        content = news.get("content", [])
        if isinstance(content, list):
            news_text = " ".join(content)
        else:
            news_text = str(content)
        news_text = news_text[:5000]  # 限制輸入長度

        triples = draft.get("triples", [])
        stats["total_triples_before"] += len(triples)

        if not triples:
            verified_results.append(draft)
            continue
            
        verified_triples_list = verify_and_fix_triples(news_text, triples)

        if verified_triples_list is None:
            print(f"Verification failed for {news_id}. Keeping original triples.")
            verified_results.append(draft)
            stats["kept"] += len(triples)
            stats["total_triples_after"] += len(triples)
            continue

        # 建立 (head, tail) 到 triple 的映射
        verified_map = {(v["head"], v["tail"]): v for v in verified_triples_list}

        final_triples = []
        
        for original_triple in triples:
            key = (original_triple["head"], original_triple["tail"])
            
            # 如果 GPT 有回傳這個 triple 的驗證結果
            if key in verified_map:
                verified = verified_map[key]
                action = verified.get("action", "KEEP")
                
                if action == "DELETE":
                    stats["deleted"] += 1
                    continue
                
                new_triple = original_triple.copy()
                new_triple["relation"] = verified.get("relation", original_triple["relation"])
                
                # 再次檢查 Relation 是否在白名單內
                if new_triple["relation"] not in VALID_RELATIONS:
                     new_triple["relation"] = "REPORTS"

                final_triples.append(new_triple)
                
                if action == "MODIFY":
                    stats["modified"] += 1
                else:
                    stats["kept"] += 1
            else:
                # 若 GPT 漏掉驗證，預設保留
                final_triples.append(original_triple)
                stats["kept"] += 1
        
        stats["total_triples_after"] += len(final_triples)
        
        # 更新結果
        draft["triples"] = final_triples
        verified_results.append(draft)
        
        time.sleep(0.5)
    
    # 輸出檔案設定
    output_dir = os.path.dirname(draft_file)
    output_filename = f"{ticker.lower()}_triples_verified.json"
    output_path = os.path.join(output_dir, output_filename)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(verified_results, f, ensure_ascii=False, indent=2)
    
    print(f"\nVerification Stats for {ticker}:")
    print(f"  Before: {stats['total_triples_before']} triples")
    print(f"  After:  {stats['total_triples_after']} triples")
    print(f"  Deleted: {stats['deleted']}, Modified: {stats['modified']}")
    print(f"Saved to: {output_path}")
    
    return output_path

if __name__ == "__main__":
    user_ticker = input("Please enter the stock ticker (e.g., PLTR): ").strip().upper()
    
    if user_ticker:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        test_news_path = os.path.join(current_dir, "..", "output", f"{user_ticker.lower()}_data", f"{user_ticker.lower()}_news.json")
        test_draft_path = os.path.join(current_dir, "..", "output", f"{user_ticker.lower()}_data", f"{user_ticker.lower()}_triples_zero_shot.json")
        
        print(f"News Source: {test_news_path}")
        print(f"Draft Triples: {test_draft_path}")
        
        if os.path.exists(test_news_path) and os.path.exists(test_draft_path):
            result_path = run_auto_verifier(test_draft_path, test_news_path, user_ticker)
            print(f"Next step input file: {result_path}")
        else:
            print("Test files not found. Please run the previous module to generate the necessary input files.")