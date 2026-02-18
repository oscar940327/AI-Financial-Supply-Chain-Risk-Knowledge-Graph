import os 
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def load_json(filepath):
    if not os.path.exists(filepath):
        print(f"File {filepath} does not exist.")
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
    
# 呼叫 LLM 來分析市場情緒
def analyze_market_sentiment(triples, ticker):
    triples_str = json.dumps(triples, ensure_ascii=False, indent=2)

    prompt  = f"""
    You are a senior Wall Street quantitative analyst. 
    Your task is to analyze the short-term market sentiment for the stock "{ticker}" based ONLY on the provided Knowledge Graph Triples.
    
    ### Input Knowledge Graph Triples:
    {triples_str}
    
    ### Analytical Instructions:
    1. **Evaluate Concrete Data**: Look for earnings reports, revenue numbers, and guidance (e.g., "INCREASES EPS estimate", "REPORTS revenue growth").
    2. **Assess Strategic Moves**: Look for partnerships, product launches (AIP, Foundry), or expansions (e.g., "EXPANDS presence").
    3. **Weigh Risks**: Look for "WARNS", "DECREASES", or short-selling activities (e.g., Michael Burry's position).
    4. **Synthesize**: Combine these factors into a single sentiment signal.

    ### Output Format (JSON ONLY):
    {{
        "signal": "Bullish" | "Bearish" | "Neutral",
        "score": <integer from -10 (extreme bearish) to 10 (extreme bullish)>,
        "key_drivers": [
            "<Reasoning 1 citing specific triples>",
            "<Reasoning 2 citing specific triples>",
            "<Reasoning 3 citing specific triples>"
        ],
        "summary": "<A concise paragraph (in Traditional Chinese) summarizing the overall investment narrative based on the graph.>"
    }}
    """

    try: 
        response = client.chat.completions.create(
            model="gpt-5.2",
            messages=[
                {"role": "system", "content": "You are a financial analyst. Output valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Error analyzing market sentiment: {e}")
        return None
    
# 呼叫 LLM 來分析市場情緒
def run_market_sentiment(input_file, ticker):
    print(f"Starting Market Sentiment Analysis for {ticker}...")

    input_file = os.path.normpath(input_file)
    data = load_json(input_file)

    if not data:
        print("No data found or failed to load. Exiting.")
        return None
    
    # 將所有三元組合併成一個列表
    all_triples = []
    for news in data:
        all_triples.extend(news.get("triples", []))

    print(f"Aggregated {len(all_triples)} triples from {len(data)} news articles.")

    if not all_triples:
        print("No triples found in the data. Exiting.")
        return None
    
    # 執行分析
    analysis_result = analyze_market_sentiment(all_triples, ticker)

    if analysis_result:
        # 顯示簡單報告
        signal = analysis_result.get("signal", "Neutral")
        score = analysis_result.get("score", 0)
        print(f"\n[{ticker}] Market Sentiment: {signal} (Score: {score})")
        print("Summary:", analysis_result.get("summary"))

        # 存檔
        output_file = os.path.dirname(input_file)
        output_filename = f"{ticker.lower()}_sentiment.json"
        output_path = os.path.join(output_file, output_filename)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(analysis_result, f, ensure_ascii=False, indent=4) 

        print(f"Sentiment analysis saved to: {output_path}")
        return output_path
    else:
        print("Analysis failed.")
        return None
    
if __name__ == "__main__":
    # 單檔測試區塊
    user_ticker = input("Please enter the stock ticker (e.g., PLTR): ").strip().upper()

    if user_ticker:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        test_input_path = os.path.join(current_dir, "..", "output", f"{user_ticker.lower()}_data", f"{user_ticker.lower()}_triples_verified.json")

        print(f"Reading from: {test_input_path}")

        if os.path.exists(test_input_path):
            run_market_sentiment(test_input_path, user_ticker)
        else:
            print(f"File {test_input_path} does not exist. Please ensure the data file is in place.")