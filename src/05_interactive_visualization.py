# -*- coding: utf-8 -*-
import os
import json
import networkx as nx
from pyvis.network import Network

# 定義顏色配置
COLOR_MAP = {
    "Company": "#00d4ff",   # 藍綠色
    "Product": "#ffea00",   # 黃色 
    "Risk": "#ff4d4d",      # 紅色 
    "Event": "#bd8cbf",     # 紫色
    "Person": "#ffa500",    # 橘色
    "Entity": "#97c2fc"     # 預設淺藍
}

# 讀取 JSON
def load_json(filepath):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

# 推斷實體類型
def infer_entity_type(entity_name, ticker):
    name_lower = entity_name.lower()
    ticker_lower = ticker.lower()
    
    # 核心目標
    if ticker_lower in name_lower:
        return "Company"
    
    # 風險關鍵字
    if any(x in name_lower for x in ["risk", "concern", "short", "warning", "decline", "loss", "debt"]):
        return "Risk"
    
    # 財務數據/事件
    if any(x in name_lower for x in ["revenue", "eps", "margin", "guidance", "$", "%"]):
        return "Event"
        
    return "Entity"

# 建立 NetworkX 圖形
def build_graph(data, ticker):
    G = nx.DiGraph()

    for news in data:
        for triple in news.get("triples", []):
            head = triple.get("head").strip()
            tail = triple.get("tail").strip()
            relation = triple.get("relation")

            head_type = infer_entity_type(head, ticker)
            tail_type = infer_entity_type(tail, ticker)

            G.add_node(head, label=head, title=head, color=COLOR_MAP.get(head_type, "#97c2fc"), group=head_type)
            G.add_node(tail, label=tail, title=tail, color=COLOR_MAP.get(tail_type, "#97c2fc"), group=tail_type)

            G.add_edge(head, tail, title=relation, label=relation, arrows="to")

    # 根據 degree 動態設定節點大小
    degrees = dict(G.degree())
    for node in G.nodes():
        degree = degrees.get(node, 1)
        # degree 1 → size 10, degree 10+ → size 40, 上限 50
        size = min(10 + degree * 3, 50)
        G.nodes[node]["size"] = size

    return G

# 
def inject_watermark(html_path, sentiment_data):
    if not sentiment_data:
        return

    # 根據情緒決定顏色
    signal = sentiment_data.get("signal", "Neutral")
    if signal == "Bullish":
        border_color = "#00E676" # 螢光綠
        text_color = "#00E676"
    elif signal == "Bearish":
        border_color = "#FF1744" # 螢光紅
        text_color = "#FF1744"
    else:
        border_color = "#FFC400" # 橘黃
        text_color = "#FFC400"

    score = sentiment_data.get("score", 0)
    summary = sentiment_data.get("summary", "No summary available.")

    # 設計浮水印的 HTML/CSS
    watermark_html = f"""
    <div style="
        position: fixed; 
        bottom: 20px; 
        right: 20px; 
        width: 350px;
        background-color: rgba(10, 10, 10, 0.90); 
        border: 2px solid {border_color}; 
        border-radius: 10px; 
        padding: 20px; 
        z-index: 1000; 
        font-family: Arial, sans-serif; 
        box-shadow: 0 0 15px rgba(0,0,0,0.8);
        color: #ddd;
        backdrop-filter: blur(4px);
    ">
        <h3 style="margin-top: 0; color: {text_color}; border-bottom: 1px solid #444; padding-bottom: 10px;">
            MARKET SENTIMENT: {signal.upper()}
            <span style="font-size: 0.8em; float: right; color: #fff;">Score: {score}</span>
        </h3>
        <p style="font-size: 14px; line-height: 1.6; text-align: justify; margin-bottom: 0;">
            {summary}
        </p>
    </div>
    """

    # 讀取原始 HTML
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 在 </body> 前插入浮水印
    if "</body>" in content:
        new_content = content.replace("</body>", f"{watermark_html}\n</body>")
        
        # 寫回檔案
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(" -> Watermark injected successfully.")
    else:
        print(" -> Error: Could not find </body> tag to inject watermark.")

# 執行視覺化流程
def run_visualization(ticker):
    print(f"Starting Visualization for {ticker}...")
    
    # 設定檔案路徑
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.join(current_dir, "..", "output", f"{ticker.lower()}_data")
    
    triples_path = os.path.join(base_dir, f"{ticker.lower()}_triples_verified.json")
    sentiment_path = os.path.join(base_dir, f"{ticker.lower()}_sentiment.json")
    output_html_path = os.path.join(base_dir, f"{ticker.lower()}_knowledge_graph.html")

    # 讀取資料
    triples_data = load_json(triples_path)
    sentiment_data = load_json(sentiment_path)

    if not triples_data:
        print("No knowledge graph data found. Please run previous steps first.")
        return None

    # 建立圖譜
    print(f"Building graph from {len(triples_data)} documents...")
    G = build_graph(triples_data, ticker)
    
    # 使用 Pyvis 生成基礎 HTML
    net = Network(height="900px", width="100%", bgcolor="#111111", font_color="white", directed=True)
    net.from_nx(G)
    
    # 調整物理引擎參數
    net.force_atlas_2based(
        gravity=-50,
        central_gravity=0.01,
        spring_length=120,
        spring_strength=0.08,
        damping=0.4,
        overlap=0
    )
    
    # 存檔 
    net.write_html(output_html_path)
    print(f"Graph generated at: {output_html_path}")

    # 注入浮水印
    if sentiment_data:
        print("Injecting sentiment analysis watermark...")
        inject_watermark(output_html_path, sentiment_data)
    else:
        print("Warning: No sentiment data found. Skipping watermark.")

    return output_html_path

if __name__ == "__main__":
    # 單檔測試
    user_ticker = input("Please enter the stock ticker (e.g., PLTR): ").strip().upper()
    if user_ticker:
        result = run_visualization(user_ticker)
        if result:
            print(f"\nVisualization Complete! Open this file in your browser:\n{result}")