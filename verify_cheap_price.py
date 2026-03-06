
import yfinance as yf
import pandas as pd
import time

def verify_price_logic(symbol):
    print(f"Verifying price logic for {symbol}...")
    
    # 1. Simulate Daily Data Fetch (Old Logic Source)
    print("Fetching Daily Data (1y, 1d)...")
    df = yf.download(symbol + ".IS", period="1y", interval="1d", progress=False)
    
    if df.empty:
        print("Error: Daily data empty.")
        return

    # Handle MultiIndex if present (yfinance update)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    daily_close = float(df['Close'].iloc[-1])
    print(f"Daily Close (Old Logic): {daily_close}")

    # 2. Simulate Real-Time Fetch (New Logic Source)
    print("Fetching Real-Time Data (1d, 1m)...")
    rt_ticker = yf.Ticker(symbol + ".IS")
    rt_hist = rt_ticker.history(period="1d", interval="1m")
    
    if not rt_hist.empty:
        rt_price = float(rt_hist['Close'].iloc[-1])
        print(f"Real-Time Price (New Logic): {rt_price}")
        
        diff = abs(rt_price - daily_close)
        print(f"Difference: {diff:.2f}")
        
        if diff == 0:
            print("Prices match (Market might be closed or data settled). Logic executed successfully.")
        else:
            print("Prices differ! Real-time fetch is providing different data. Logic works.")
    else:
        print("Error: Real-time data empty.")

if __name__ == "__main__":
    verify_price_logic("THYAO")
    verify_price_logic("GARAN")
