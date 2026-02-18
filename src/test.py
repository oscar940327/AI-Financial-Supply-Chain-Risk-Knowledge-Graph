# -*- coding: utf-8 -*-
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import json
import time
import os

# 偽裝成瀏覽器
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# 使用 yfinance 獲取指定股票的最新新聞列表
def fetch_news_list(ticker):
    print(f"Fetching news list for ticker: {ticker}")
    stock = yf.Ticker(ticker)
    news_list = stock.news
    print(f"Fetched {len(news_list)} news items.")
    return news_list

# 進入新聞網址，抓取內文並進行初步清洗
def scrape_content(url):
    try:
        time.sleep(1)
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            print(f"Failed to fetch {url}: Status code {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        paragraphs = soup.find_all('p')
        clean_paragraphs = []

        for p in paragraphs:
            text = p.get_text().strip()
            if len(text) > 30:
                clean_paragraphs.append(text)

        if not clean_paragraphs:
            return None
        return clean_paragraphs
    
    except Exception as e:
        print(f"Error fetching content from {url}: {e}")
        return None
    
# 主函數，負責整合流程並回傳生成的檔案路徑
def run_data_collection(ticker):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 動態生成資料夾名稱，例如 output/tsla_data
    output_dir = os.path.join(current_dir, "..", "output", f"{ticker.lower()}_data")
    output_dir = os.path.normpath(output_dir)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")

    news_items = fetch_news_list(ticker)
    collected_data = []

    for i, item in enumerate(news_items):
        item_content = item.get('content', {})
        title = item_content.get('title')
        link = item_content.get('canonicalUrl', {}).get('url')
        publisher = item_content.get('provider', {}).get('displayName')
        publish_time = item_content.get('pubDate')

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

    # 檔名動態生成
    output_file = os.path.join(output_dir, f"{ticker.lower()}_news.json")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(collected_data, f, ensure_ascii=False, indent=4)

    print(f"\n Execution completed! Successfully scrapped {len(collected_data)} news articles")
    print(f"File saved to: {output_file}")
    
    return output_file

if __name__ == "__main__":
    user_ticker = input("請輸入要抓取新聞的股票代號 (例如 TSLA, NVDA): ").strip().upper()
    
    if user_ticker:
        result_path = run_data_collection(user_ticker)
        print(f"測試完成，檔案路徑準備交給下一個模組: {result_path}")
    else:
        print("未輸入股票代號，程式結束。")