import streamlit as st
import os
import sys
import importlib.util
import time
import streamlit.components.v1 as components

# 設定網頁標題與寬度
st.set_page_config(page_title="AI Supply Chain Analyst", layout="wide")

# 動態匯入模組函數
def import_module_from_file(module_name, file_name):
    file_path = os.path.join(os.path.dirname(__file__), file_name)
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# 載入所有模組 (快取以避免重複載入)
@st.cache_resource
def load_modules():
    try:
        m1 = import_module_from_file("mod_01", "01_data_collection.py")
        m2 = import_module_from_file("mod_02", "02_llm_extraction.py")
        m3 = import_module_from_file("mod_03", "03_auto_verifier.py")
        m4 = import_module_from_file("mod_04", "04_market_sentiment.py") 
        m5 = import_module_from_file("mod_05", "05_interactive_visualization.py")
        return m1, m2, m3, m4, m5
    except Exception as e:
        st.error(f"Failed to load modules: {e}")
        return None, None, None, None, None

mod_01, mod_02, mod_03, mod_04, mod_05 = load_modules()

# UI 介面設計
st.title("AI Financial Supply Chain Risk Analyzer")
st.markdown("Enter a stock ticker to automatically run: News Crawling -> Knowledge Extraction -> Relation Verification -> Sentiment Analysis -> Knowledge Graph")

# 側邊欄輸入
with st.sidebar:
    st.header("Control Panel")
    ticker = st.text_input("Stock Ticker", value="PLTR").upper()
    run_btn = st.button("Start Analysis", type="primary")

# 主執行邏輯
if run_btn and ticker:
    status_area = st.empty()
    progress_bar = st.progress(0)
    
    try:
        # Step 1
        status_area.info(f"Step 1: Crawling news for {ticker}...")
        news_file = mod_01.run_data_collection(ticker)
        progress_bar.progress(20)
        
        # Step 2
        status_area.info("Step 2: Running LLM knowledge triple extraction (this may take a while)...")
        draft_file = mod_02.run_llm_extraction(news_file, ticker)
        progress_bar.progress(40)
        
        # Step 3
        status_area.info("Step 3: Running GPT auto verification and cleaning...")
        verified_file = mod_03.run_auto_verifier(draft_file, news_file, ticker)
        progress_bar.progress(60)
        
        # Step 4
        status_area.info("Step 4: Analyzing market sentiment...")
        sentiment_file = mod_04.run_market_sentiment(verified_file, ticker)
        progress_bar.progress(80)
        
        # Step 5
        status_area.info("Step 5: Generating interactive knowledge graph...")
        html_path = mod_05.run_visualization(ticker)
        progress_bar.progress(100)
        
        status_area.success("Analysis completed!")
        
        # 顯示結果
        st.subheader(f"{ticker} Supply Chain Risk Knowledge Graph")
        
        # 讀取 HTML 並顯示在網頁中
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # 使用 iframe 嵌入互動圖表
        components.html(html_content, height=850, scrolling=True)
        
        # 提供下載按鈕
        with open(html_path, "rb") as f:
            st.download_button(
                label="Download HTML Report",
                data=f,
                file_name=f"{ticker}_report.html",
                mime="text/html"
            )

    except Exception as e:
        status_area.error(f"An error occurred during execution: {str(e)}")