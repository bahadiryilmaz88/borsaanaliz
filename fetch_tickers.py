
import requests
import json

def fetch_tickers():
    url = "https://raw.githubusercontent.com/ahmeterenodaci/Istanbul-Stock-Exchange--BIST--including-symbols-and-logos/main/data/BIST_Companies_Without_Logo.csv"
    try:
        # Some headers to look like a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        requests.packages.urllib3.disable_warnings()
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        if response.status_code == 200:
            lines = response.text.splitlines()
            tickers = []
            # CSV format: symbol,name,...
            for line in lines[1:]: # Skip header
                parts = line.split(',')
                if parts:
                    tickers.append(parts[0].strip())
            
            print(f"Fetched {len(tickers)} tickers.")
            print("First 10:", tickers[:10])
            
            # Save to file
            with open('bist_full.json', 'w') as f:
                json.dump(tickers, f)
        else:
            print(f"Failed with status {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")

fetch_tickers()
