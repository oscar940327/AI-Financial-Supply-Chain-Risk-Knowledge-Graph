# -*- coding: utf-8 -*-
import os
import json
import time
import requests
import yfinance as yf
from bs4 import BeautifulSoup

# 偽裝成瀏覽器
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# 使用 yfinance 獲取指定股票的最新新聞列表
def fetch_news_list(ticker):
    print(f"Fetching news list for ticker: {ticker}")

    # 1. 建立一個 Ticker 物件，代號 TSLA
    stock = yf.Ticker(ticker)

    # 2. 獲取新聞列表
    news_list = stock.news

    print(f"Fetched {len(news_list)} news items.")
    return news_list

# 進入新聞網址，抓取內文並進行初步清洗
def scrape_content(url):
    try:
        # 1. 避免過快請求
        time.sleep(1)

        # 2. 發送請求
        response = requests.get(url, headers=HEADERS, timeout=10)

        # 確認能否讀取網頁
        if response.status_code != 200:
            print(f"Failed to fetch {url}: Status code {response.status_code}")
            return None

        # 3. 解析 HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # 4. 鎖定目標標籤
        paragraphs = soup.find_all('p')

        # 準備一個列表來存放清洗後的段落
        clean_paragraphs = []

        # 5. 提取文字並清洗
        for p in paragraphs:
            text = p.get_text().strip()

            # 只留長度大於 50 的段落，避免過短的無意義內容
            if len(text) > 30:
                clean_paragraphs.append(text)

        # 如果沒有找到合適的段落，返回 None
        if not clean_paragraphs:
            return None
        
        # 6. 返回清洗後的段落列表
        return clean_paragraphs
    
    except Exception as e:
        print(f"Error fetching content from {url}: {e}")
        return None
    
# 負責整合流程
def run_data_collection(ticker):
    # 建立資料夾存放資料
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 讓資料夾名稱也根據股票代號動態生成，例如 output/tsla_data
    output_dir = os.path.join(current_dir, "..", "output", f"{ticker.lower()}_data")
    output_dir = os.path.normpath(output_dir)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")

    # 獲取新聞列表
    news_items = fetch_news_list(ticker)
    collected_data = []

    # 處理每條新聞
    for i, item in enumerate(news_items):
        item_content = item.get('content', {})
        title = item_content.get('title')
        link = item_content.get('canonicalUrl', {}).get('url')
        publisher = item_content.get('provider', {}).get('displayName')
        publish_time = item_content.get('pubDate')

        if not title or not link:
            print(f"Skipping item with missing title or link: {item}")
            continue

        print(f"Processing ({i+1}/{len(news_items)}): {title}")

        content_paragraphs = scrape_content(link)

        if content_paragraphs:
            news_entry = {
                "news_id": f"news_{publish_time}",
                "title": title,
                "url": link,
                "publisher": publisher,
                "publish_time": publish_time,
                "content": content_paragraphs
            }
            collected_data.append(news_entry)
        else:
            print(f" -> Skipped (Failed to fetch content or content too short)")

    # 將結果儲存為 JSON 檔案
    output_file = os.path.join(output_dir, f"{ticker.lower()}_news.json")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(collected_data, f, ensure_ascii=False, indent=4)

    print(f"\n Execution completed! Successfully scrapped {len(collected_data)} news articles")
    print(f"File saved to: {output_file}")
    
    return output_file

if __name__ == "__main__":
    # 在這裡處理終端機的輸入
    user_ticker = input("Please enter the stock ticker (e.g., TSLA, NVDA): ").strip().upper()
    
    if user_ticker:
        # 呼叫主函數並傳入使用者輸入的代號
        result_path = run_data_collection(user_ticker)
        print(f"Testing completed, file path ready to be passed to the next module: {result_path}")
    else:
        print("No stock ticker entered, program terminated.")