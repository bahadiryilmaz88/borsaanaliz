from tradingview_ta import TA_Handler, Exchange, Interval
import json
import time

def fetch_all_bist():
    print("Fetching all BIST stocks from TradingView...")
    
    # We can't directly "list all" easily with standard TA_Handler without a screener query.
    # But we can use the `get_analysis` method on a massive list if we had it, OR use a raw request which `tradingview_ta` doesn't purely expose for *listing*.
    # WAIT: `tradingview_ta` is for analysis, NOT for fetching the symbol list itself efficiently.
    # However, we can use a known "All Stocks" fetcher trick or just a standard vast list approach.
    
    # BETTER APPROACH: Use `requests` to hit the TV scanner API directly, which is what the library does internally but we need the LIST.
    
    import requests

    url = "https://scanner.tradingview.com/turkey/scan"
    
    payload = {
        "filter": [
            {"left": "type", "operation": "in_range", "right": ["stock", "dr", "fund"]}, 
            {"left": "exchange", "operation": "equal", "right": "BIST"},
            {"left": "subtype", "operation": "in_range", "right": ["common", "foreign-issuer"]} # Exclude warrants if possible
        ],
        "options": {"lang": "tr"},
        "symbols": {"query": {"types": []}},
        "columns": ["name", "description", "close", "volume", "type", "subtype"],
        "sort": {"sortBy": "volume", "sortOrder": "desc"},
        "range": [0, 1000] # Fetch top 1000 by volume (BIST has ~600 stocks so this covers all)
    }

    try:
        response = requests.post(url, json=payload)
        data = response.json()
        
        tickers = []
        count = 0
        
        print(f"Total entries found: {data['totalCount']}")
        
        for item in data['data']:
            symbol = item['d'][0]
            desc = item['d'][1]
            subtype = item['d'][5]
            
            # Filter out some non-equity types if needed
            if subtype in ['etf', 'warrant']: continue
            
            tickers.append(symbol)
            count += 1
            
        tickers.sort()
        
        print(f"Filtered Stock Count: {len(tickers)}")
        
        # Save
        with open('bist_full.json', 'w', encoding='utf-8') as f:
            json.dump(tickers, f, indent=4)
            
        print("Success! Saved to bist_full.json")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fetch_all_bist()
