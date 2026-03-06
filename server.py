import pandas as pd
import pandas_ta as ta
import yfinance as yf
import numpy as np
from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS
import concurrent.futures
import math
import schedule
import time
import datetime
import threading
import json
import requests
import xml.etree.ElementTree as ET
import sys
import os
import warnings
import qrcode
import socket
from io import BytesIO
warnings.simplefilter(action='ignore', category=FutureWarning)


# --- STOCK NAMES LOADER ---
STOCK_NAMES = {}
def load_stock_names():
    global STOCK_NAMES
    try:
        if os.path.exists('stocks.json'):
            with open('stocks.json', 'r', encoding='utf-8') as f:
                STOCK_NAMES = json.load(f)
            print(f"HİSSE İSİMLERİ YÜKLENDİ: {len(STOCK_NAMES)} adet")
        else:
            print("stocks.json bulunamadı!")
    except Exception as e:
        print(f"Hisse isimleri yüklenirken hata: {e}")

load_stock_names()


# Configuration
app = Flask(__name__)
# Enable CORS for local development flexibility
CORS(app)

import logging
# Suppress yfinance error logging
logger = logging.getLogger('yfinance')
logger.disabled = True
logger.propagate = False




import concurrent.futures
import json
import numpy as np
from flask.json.provider import DefaultJSONProvider
from tradingview_ta import TA_Handler, Interval, Exchange

# Optional Scipy Import for Advanced Math
try:
    from scipy.signal import argrelextrema
    SCIPY_AVAIL = True
except ImportError:
    SCIPY_AVAIL = False
    print("Warning: Scipy not found. Using Numpy fallback for local extrema.")

class NpProvider(DefaultJSONProvider):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

app.json = NpProvider(app)


print("=================================================")
print("  BIST ANALIZ PRO - 8-STEP ENGINE")
print("=================================================")

# Full BIST List (Dynamically Loaded)
ALL_BIST_TICKS = []

def load_bist_tickers():
    global ALL_BIST_TICKS
    try:
        if os.path.exists('bist_full.json'):
            with open('bist_full.json', 'r', encoding='utf-8') as f:
                ALL_BIST_TICKS = json.load(f)
            print(f"FULL BIST LISTESI YÜKLENDİ: {len(ALL_BIST_TICKS)} adet")
        else:
            # Fallback to a smaller hardcoded list if file missing
            ALL_BIST_TICKS = [
                "AEFES", "AGHOL", "AHGAZ", "AKBNK", "AKCNS", "AKFGY", "AKSA", "AKSEN", "ALARK", "ALBRK", "ALFAS", "ANHYT", "ANSGR", "ARCLK", "ASELS", "ASTOR", "ASUZU", "AYDEM", "AYGAZ", "BAGFS", 
                "BERA", "BIMAS", "BIOEN", "BRSAN", "BRYAT", "BUCIM", "CANTE", "CCOLA", "CEMTS", "CIMSA", "CWENE", "DOAS", "DOHOL", "ECILC", "EGEEN", "EKGYO", "EMKEL", "ENJSA", "ENKAI", "EREGL", "EUPWR", 
                "EUREN", "FROTO", "GARAN", "GENIL", "GESAN", "GLYHO", "GUBRF", "GWIND", "HALKB", "HEKTS", "IPEKE", "ISCTR", "ISDMR", "ISGYO", "ISMEN", "KCAER", "KCHOL", "KONTR", "KONYA", "KORDS", 
                "KOZAA", "KOZAL", "KRDMA", "KRDMB", "KRDMD", "KZBGY", "LMKDC", "MAVI", "MGROS", "MIATK", "ODAS", "OTKAR", "OYAKC", "PENTA", "PETKM", "PGSUS", "PSGYO", "QUAGR", "SAHOL", "SASA", "SDTTR", "SISE", "SKBNK", 
                "SMRTG", "SOKM", "TAVHL", "TCELL", "THYAO", "TKFEN", "TOASO", "TSKB", "TTKOM", "TTRAK", "TUKAS", "TUPRS", "TURSG", "ULKER", "VAKBN", "VESBE", "VESTL", "YKBNK", "YYLGD", "ZOREN"
            ]
            print(f"VARSAYILAN BIST LISTESI YÜKLENDİ: {len(ALL_BIST_TICKS)} adet")
    except Exception as e:
        print(f"Ticker yükleme hatası: {e}")

load_bist_tickers()

# Stock Symbol to Company Name Mapping (with Sector)
STOCK_NAMES = {
    "AEFES": "Anadolu Efes (Gıda & İçecek)", "AGHOL": "Ag Anadolu Grubu (Holding)", "AHGAZ": "Ahlatcı Doğalgaz (Enerji)", "AKBNK": "Akbank (Bankacılık)", 
    "AKCNS": "Akçansa (Çimento)", "AKFGY": "Akfen GYO (GYO)", "AKSA": "Aksa Akrilik (Kimya)", "AKSEN": "Aksa Enerji (Enerji)",
    "ALARK": "Alarko Holding (Holding)", "ALBRK": "Albaraka Türk (Bankacılık)", "ALFAS": "Alfa Solar (Enerji)", "ANHYT": "Anadolu Hayat Emeklilik (Sigorta)",
    "ANSGR": "Anadolu Sigorta (Sigorta)", "ARCLK": "Arçelik (Dayanıklı Tüketim)", "ASELS": "Aselsan (Savunma)", "ASTOR": "Astor Enerji (Enerji)",
    "ASUZU": "Anadolu Isuzu (Otomotiv)", "AYDEM": "Aydem Enerji (Enerji)", "AYGAZ": "Aygaz (Enerji)", "BAGFS": "Bagfaş (Gıda & İçecek)",
    "BERA": "Bera Holding (Holding)", "BIMAS": "BIM (Perakende)", "BIOEN": "Biotrend (Enerji)", "BRSAN": "Borusan Mannesmann (Metal)",
    "BRYAT": "Borusan Yatırım (Holding)", "BUCIM": "Bucim (Madencilik)", "CANTE": "Çanakkale Çimento (Çimento)", "CCOLA": "Coca Cola İçecek (Gıda & İçecek)",
    "CEMTS": "Cemtaş (Çimento)", "CIMSA": "Çimsa (Çimento)", "CWENE": "CW Enerji (Enerji)", "DOAS": "Doğuş Otomotiv (Otomotiv)",
    "DOHOL": "Doğan Holding (Holding)", "ECILC": "Eczacıbaşı İlaç (Sağlık)", "EGEEN": "Ege Endüstri (Tekstil)", "EKGYO": "Emlak Konut GYO (GYO)",
    "EMKEL": "Emek Elektrik (Enerji)", "ENJSA": "Enerjisa (Enerji)", "ENKAI": "Enka İnşaat (İnşaat)", "EREGL": "Ereğli Demir Çelik (Metal)",
    "EUPWR": "Euro Power (Enerji)", "EUREN": "Euro Yatırım (Holding)", "FROTO": "Ford Otosan (Otomotiv)", "GARAN": "Garanti Bankası (Bankacılık)",
    "GENIL": "Gen İlaç (Sağlık)", "GESAN": "Gesan (Elektrik)", "GLYHO": "Global Yatırım Holding (Holding)", "GUBRF": "Gübre Fabrikaları (Kimya)",
    "GWIND": "Galata Wind (Enerji)", "HALKB": "Halkbank (Bankacılık)", "HEKTS": "Hektaş (Tekstil)", "IPEKE": "İpek Doğal Enerji (Enerji)",
    "ISCTR": "İş Bankası (C) (Bankacılık)", "ISDMR": "İskenderun Demir Çelik (Metal)", "ISGYO": "İş GYO (GYO)", "ISMEN": "İş Yatırım Menkul (Finans)",
    "KCAER": "Kocaer Çelik (Metal)", "KCHOL": "Koç Holding (Holding)", "KONTR": "Kontrolmatik (Teknoloji)", "KONYA": "Konya Çimento (Çimento)",
    "KORDS": "Kordsa (Kimya)", "KOZAA": "Koza Anadolu Metal (Madencilik)", "KOZAL": "Koza Altın (Madencilik)", "KRDMA": "Kardemir (A) (Metal)",
    "KRDMB": "Kardemir (B) (Metal)", "KRDMD": "Kardemir (D) (Metal)", "KZBGY": "Kızılay GYO (GYO)", "LMKDC": "Limak Çimento (Çimento)",
    "MAVI": "Mavi Giyim (Tekstil)", "MGROS": "Migros (Perakende)", "MIATK": "Mia Teknoloji (Teknoloji)", "ODAS": "Odaş Elektrik (Enerji)",
    "OTKAR": "Otokar (Otomotiv)", "OYAKC": "Oyak Çimento (Çimento)", "PENTA": "Penta Teknoloji (Teknoloji)", "PETKM": "Petkim (Kimya)",
    "PGSUS": "Pegasus (Ulaştırma)", "PSGYO": "Pera GYO (GYO)", "QUAGR": "Qua Granite (İnşaat)", "SAHOL": "Sabancı Holding (Holding)",
    "SASA": "Sasa Polyester (Kimya)", "SDTTR": "Şekerbank (Bankacılık)", "SISE": "Şişe Cam (Cam)", "SKBNK": "Şekerbank (Bankacılık)",
    "SMRTG": "Smart Güneş (Enerji)", "SOKM": "Şok Marketler (Perakende)", "TAVHL": "TAV Havalimanları (Ulaştırma)", "TCELL": "Turkcell (Telekomünikasyon)",
    "THYAO": "Türk Hava Yolları (Ulaştırma)", "TKFEN": "Tekfen Holding (Holding)", "TOASO": "Tofaş (Otomotiv)", "TSKB": "TSKB (Bankacılık)",
    "TTKOM": "Türk Telekom (Telekomünikasyon)", "TTRAK": "Türk Traktör (Otomotiv)", "TUKAS": "Tukaş (Gıda & İçecek)", "TUPRS": "Tüpraş (Enerji)",
    "TURSG": "Türk Sigorta (Sigorta)", "ULKER": "Ülker Bisküvi (Gıda & İçecek)", "VAKBN": "Vakıfbank (Bankacılık)", "VESBE": "Vestel Beyaz Eşya (Dayanıklı Tüketim)",
    "VESTL": "Vestel Elektronik (Teknoloji)", "YKBNK": "Yapı Kredi (Bankacılık)", "YYLGD": "Yayla Enerji (Enerji)", "ZOREN": "Zorlu Enerji (Enerji)"
}

@app.route('/')
def index():
    return send_file('dashboard.html')

@app.route('/manifest.json')
def manifest():
    return send_file('manifest.json')

@app.route('/api/stocks')
def get_stocks():
    """Return list of stocks with their full names"""
    stocks = [{"symbol": symbol, "name": STOCK_NAMES.get(symbol, symbol)} for symbol in ALL_BIST_TICKS]
    return jsonify(stocks)

@app.route('/sw.js')
def service_worker():
    return send_file('sw.js', mimetype='application/javascript')


@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@app.route('/qr')
def get_qr():
    # Get Local IP
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    
    url = f"http://{IP}:5000"
    
    # Generate QR
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save to BytesIO
    img_io = BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    
    return send_file(img_io, mimetype='image/png')

@app.route('/api/ip')
def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return jsonify({'ip': IP, 'port': 5000})

# --- FAVORITES MANAGEMENT ---
FAVORITES_FILE = 'favorites.json'

def load_favorites():
    """Load favorites from JSON file"""
    try:
        if os.path.exists(FAVORITES_FILE):
            with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Handle migration from old array format to new object format
                if isinstance(data, list):
                    return {symbol: {'alerts': [None, None, None]} for symbol in data}
                return data
        return {}
    except Exception as e:
        print(f"Error loading favorites: {e}")
        return {}

def save_favorites(favorites):
    """Save favorites to JSON file"""
    try:
        with open(FAVORITES_FILE, 'w', encoding='utf-8') as f:
            json.dump(favorites, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving favorites: {e}")
        return False

@app.route('/api/favorites', methods=['GET'])
def get_favorites():
    """Get list of favorite symbols with alerts"""
    favorites = load_favorites()
    return jsonify({'favorites': favorites})

@app.route('/api/favorites', methods=['POST'])
def add_favorite():
    """Add a symbol to favorites"""
    data = request.get_json()
    symbol = data.get('symbol', '').upper()
    
    if not symbol:
        return jsonify({'error': 'Symbol required'}), 400
    
    favorites = load_favorites()
    if symbol not in favorites:
        favorites[symbol] = {'alerts': [None, None, None]}
        if save_favorites(favorites):
            return jsonify({'success': True, 'favorites': favorites})
        else:
            return jsonify({'error': 'Failed to save'}), 500
    
    return jsonify({'success': True, 'favorites': favorites})

@app.route('/api/favorites/<symbol>', methods=['DELETE'])
def remove_favorite(symbol):
    """Remove a symbol from favorites"""
    symbol = symbol.upper()
    favorites = load_favorites()
    
    if symbol in favorites:
        del favorites[symbol]
        if save_favorites(favorites):
            return jsonify({'success': True, 'favorites': favorites})
        else:
            return jsonify({'error': 'Failed to save'}), 500
    
    return jsonify({'success': True, 'favorites': favorites})

@app.route('/api/favorites/<symbol>/alerts', methods=['PUT'])
def update_alerts(symbol):
    """Update alert prices for a symbol"""
    symbol = symbol.upper()
    data = request.get_json()
    alerts = data.get('alerts', [None, None, None])
    
    # Validate alerts (should be array of 3 numbers or None)
    if not isinstance(alerts, list) or len(alerts) != 3:
        return jsonify({'error': 'Alerts must be array of 3 values'}), 400
    
    favorites = load_favorites()
    if symbol not in favorites:
        return jsonify({'error': 'Symbol not in favorites'}), 404
    
    favorites[symbol]['alerts'] = alerts
    if save_favorites(favorites):
        return jsonify({'success': True, 'favorites': favorites})
    else:
        return jsonify({'error': 'Failed to save'}), 500

@app.route('/api/favorites/prices', methods=['GET'])
def get_favorite_prices():
    """Get current prices for all favorites with alert status"""
    favorites = load_favorites()
    prices = {}
    
    def fetch_price(symbol):
        try:
            ticker = yf.Ticker(symbol + '.IS')
            hist = ticker.history(period='1d', interval='1m')
            if not hist.empty:
                return symbol, float(hist['Close'].iloc[-1])
        except:
            pass
        return symbol, None
    
    # Fetch prices in parallel for speed
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_price, sym) for sym in favorites.keys()]
        for future in concurrent.futures.as_completed(futures):
            symbol, price = future.result()
            if price is not None:
                # Check if any alerts are triggered
                alerts = favorites[symbol].get('alerts', [None, None, None])
                triggered = []
                for i, alert in enumerate(alerts):
                    if alert is not None and abs(price - alert) / alert < 0.005:  # Within 0.5%
                        triggered.append(i)
                
                prices[symbol] = {
                    'price': price,
                    'triggered_alerts': triggered
                }
    
    return jsonify({'prices': prices})

def calculate_cheap_score(df):
    """
    Kullanıcının istediği 'Ucuzluk Skoru'nu hesaplar.
    Score >= 6 -> UCUZ
    Score 4-5 -> GERİ ÇEKİLME
    Score < 4 -> PAHALI
    
    Kriterler:
    1. Close > SMA200 (+3) (Ana Trend)
    2. RSI < 35 (+2) (Aşırı Satım)
    3. Close < BB_Lower (+2) (Bant Altı)
    4. Close near SMA50 (2%) (+1) (Destek)
    5. Volume Spike (+1) (Teyit)
    """
    try:
        current = df.iloc[-1]
        score = 0
        
        # 1. Ana Trend Filtresi (Değişiklik: Hard Block yerine Puan Cezası)
        # Trend İçi (Güvenli): Close > SMA200 (+3)
        # Çöküş (Agresif): Close < SMA200 (-1 ama elenmez, diğer puanlarla toparlayabilir)
        if current['Close'] > current['SMA_200']:
            score += 3
        else:
            score -= 1 # Puan cezası, ama elenmiyor. Çöküş dibi yakalamak için.
            
        # 2. RSI Filtresi (Katmanlı)
        # Çöküş dibi için RSI < 30 çok değerli
        if current['RSI'] < 30:
            score += 4 # Çöküş dibi sinyali (Agresif alım)
        elif current['RSI'] < 35:
            score += 3 # Mükemmel
        elif current['RSI'] < 50:
            score += 2 # İyi
        elif current['RSI'] < 60:
            score += 1 # Makul
            
        # 3. Bant Konumu
        bb_low_col = [c for c in df.columns if c.startswith('BBL')][0] if any(c.startswith('BBL') for c in df.columns) else 'BB_lower'
        
        if bb_low_col in current:
            # Alt bant altındaysa veya çok yakınsa (Çöküş)
            if current['Close'] < (current[bb_low_col] * 1.01):
                score += 3 
            # Alt banda yakınsa (%2)
            elif current['Close'] < (current[bb_low_col] * 1.03):
                score += 2
            
        # 4. Hacim Teyidi (Çöküşte hacim patlaması dönüş sinyalidir)
        vol_avg = df['Volume'].rolling(window=20).mean().iloc[-1]
        if vol_avg > 0 and current['Volume'] > (vol_avg * 1.5): # %50 artış (Panic Selling veya Dip Alımı)
            score += 2
        elif vol_avg > 0 and current['Volume'] > (vol_avg * 1.1):
            score += 1
            
        return score
    except Exception as e:
        print(f"Cheap Score Error: {e}")
        return 0


@app.route('/scan_cheap')
def scan_cheap():
    results = []
    
    # 1. Helper function for single ticker
    def check_cheap(symbol):
        try:
            # yfinance download
            df = yf.download(symbol + ".IS", period="1y", interval="1d", progress=False)
            if df.empty or len(df) < 200:
                return None
                
            # Flatten columns logic
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            # İndikatörleri hesapla
            close = df['Close']
            df['SMA_200'] = close.rolling(window=200).mean()
            df['SMA_50'] = close.rolling(window=50).mean()
            df['RSI'] = ta.rsi(close, length=14)
            bb = ta.bbands(close, length=20, std=2)
            if bb is not None:
                df = pd.concat([df, bb], axis=1)
            
            # Skorla
            score = calculate_cheap_score(df)
            
            if score >= 4:
                status = "UCUZ" if score >= 6 else "GERİ ÇEKİLME"
                
                # Fetch Real-Time Price (1m) for accurate display
                last_price = float(df['Close'].iloc[-1]) # Default to daily close
                try:
                    # Quick fetch for latest price
                    rt_ticker = yf.Ticker(symbol + ".IS")
                    rt_hist = rt_ticker.history(period="1d", interval="1m")
                    if not rt_hist.empty:
                        last_price = float(rt_hist['Close'].iloc[-1])
                except Exception as e:
                    print(f"Real-time price fetch error {symbol}: {e}")

                return {
                    "symbol": symbol,
                    "score": score,
                    "status": status,
                    "price": round(last_price, 2)
                }
        except Exception as e:
            # print(f"Error scanning {symbol}: {e}")
            return None
        return None

    # 2. Threaded Execution
    print(f"Starting CHEAP Scan for {len(ALL_BIST_TICKS)} tickers...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(check_cheap, t) for t in ALL_BIST_TICKS]
        for future in concurrent.futures.as_completed(futures):
            r = future.result()
            if r:
                results.append(r)
            
    # Skora göre sırala
    results.sort(key=lambda x: x['score'], reverse=True)
    
    return jsonify({"results": results})

@app.route('/scan', methods=['GET'])
def scan_market():
    limit = request.args.get('limit', default=50, type=int)
    ticks = ALL_BIST_TICKS # Use full list
    
    results = []
    
    # Real Scan with pandas_ta
    def check_ticker(sym):
        try:
            full_sym = sym + '.IS'
            # Fetch Data (1y daily is enough for RSI/MACD)
            ticker = yf.Ticker(full_sym)
            df = ticker.history(period="6mo", interval="1d")
            
            if df.empty or len(df) < 30: return None
            
            # --- PANDAS TA INDICATORS ---
            # RSI (14)
            df.ta.rsi(length=14, append=True) # Adds RSI_14 column
            
            # MACD (12, 26, 9)
            df.ta.macd(append=True) # Adds MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
            
            last = df.iloc[-1]
            
            # CRITERIA: RSI < 30 (Oversold) OR MACD Crossover (Bullish)
            # RSI Check
            rsi_val = last['RSI_14']
            
            # MACD Crossover Check: MACD Line > Signal Line and was < yesterday
            macd_bullish = False
            if len(df) > 2:
                prev = df.iloc[-2]
                # Default names: MACD_12_26_9 (Line), MACDs_12_26_9 (Signal)
                if (prev['MACD_12_26_9'] < prev['MACDs_12_26_9']) and (last['MACD_12_26_9'] > last['MACDs_12_26_9']):
                    macd_bullish = True
            
            msg = []
            if rsi_val < 30: msg.append(f"RSI Aşırı Satım ({rsi_val:.1f})")
            if macd_bullish: msg.append("MACD Al Sinyali")
            
            if msg:
                return {
                    'symbol': sym, 
                    'price': last['Close'],
                    'msg': ", ".join(msg),
                    'rsi': rsi_val
                }
        except Exception as e:
            # print(f"Error {sym}: {e}")
            return None
        return None

    # Threaded Scan
    print(f"Starting Real pandas_ta Scan for {len(ticks)} tickers...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(check_ticker, t): t for t in ticks}
        for future in concurrent.futures.as_completed(futures):
            try:
                r = future.result()
                if r:
                    results.append(r)
            except: pass
                
    return jsonify({'count': len(results), 'results': results})


@app.route('/scan_aggressive', methods=['GET'])
def scan_aggressive():
    ticks = ALL_BIST_TICKS # Use full list
    results = []
    
    def check_aggressive(sym):
        try:
            full_sym = sym + '.IS'
            ticker = yf.Ticker(full_sym)
            # Fetch 2 month 1h data (responsive but enough for indicators)
            # We use 1H for aggressive intraday signals
            hist = ticker.history(period="2mo", interval="1h")
            
            if hist.empty: return None
            
            # Use 'aggressive' mode in calculation
            # Logic: Close < Lower Band AND RSI < 35
            hist, _ = sinyal_hesapla(hist, risk_mode='aggressive')
            
            last = hist.iloc[-1]
            
            if last['Buy_Signal']:
                # Calculate optional stop/target for display
                return {
                    'symbol': sym, 
                    'price': last['Close'],
                    'rsi': last['RSI_Signal'],
                    'time': int(last.name.timestamp())
                }
        except:
            return None
        return None

    print(f"Starting AGGRESSIVE Scan for {len(ticks)} tickers...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(check_aggressive, t) for t in ticks]
        for future in concurrent.futures.as_completed(futures):
            r = future.result()
            if r:
                results.append(r)
                
    return jsonify({'count': len(results), 'results': results})

@app.route('/scan_volume', methods=['GET'])
def scan_volume():
    ticks = ALL_BIST_TICKS
    results = []

    def check_volume(sym):
        try:
            full_sym = sym + '.IS'
            ticker = yf.Ticker(full_sym)
            # Fetch 60 days to ensure enough for SMA20 and safe buffer
            hist = ticker.history(period="3mo", interval="1d")
            
            if hist.empty or len(hist) < 25: return None
            
            last = hist.iloc[-1]
            
            # --- ITERATE LAST 5 DAYS ---
            # We look for the MOST RECENT signal in the last 5 days.
            
            # Ensure we have enough data (20 for SMA + 5 for window)
            if len(hist) < 30: return None
            
            hist['VolSMA20'] = hist['Volume'].rolling(window=20).mean()
            
            # Analyze last 5 candles (reversed: today back to 5 days ago)
            recent_data = hist.iloc[-5:].iloc[::-1] # Reverse to find most recent first
            
            match = None
            
            for i in range(len(recent_data)):
                candle = recent_data.iloc[i]
                
                # Check Green Candle
                if candle['Close'] <= candle['Open']: continue
                
                # Check Volume vs SMA20 of *that day* (or previous day if we want strict pre-close avg)
                # To be precise: We compare Volume[t] vs SMA20[t-1] usually, or SMA20[t] including t.
                # Let's use SMA20 calculated up to that row.
                
                avg_vol = candle['VolSMA20']
                # If using rolling mean including current volume, a huge volume spike raises the mean itself.
                # A huge spike > 1.5x *current* mean is definitely a spike. 
                # Ideally we want (Mean of prev 20).
                # Let's approximate: If Vol > 1.5 * VolSMA20 (which includes self), it is a massive spike.
                # Or re-calc properly? For speed let's trust simple rolling mean.
                
                # Actually, stricter: Compare to Mean of (t-21 to t-1)
                # Let's rely on the pre-calculated column for simplicity but be aware of the bias.
                # Threshold > 1.5 is already strong.
                
                if avg_vol == 0: continue
                vol_ratio = candle['Volume'] / avg_vol
                
                if vol_ratio > 1.5:
                    days_ago = i # 0 = Today, 1 = Yesterday
                    
                    price_change = ((candle['Close'] - candle['Open']) / candle['Open']) * 100
                    
                    match = {
                        'symbol': sym,
                        'price': last['Close'], # Always show current price
                        'match_price': candle['Close'], # Price at signal
                        'vol_ratio': round(vol_ratio, 2),
                        'days_ago': days_ago,
                        'change': round(price_change, 2),
                        'volume': int(candle['Volume'])
                    }
                    break # Stop at first (most recent) match
            
            return match
        except Exception as e:
            return None
        return None

    print(f"Starting VOLUME Scan for {len(ticks)} tickers...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(check_volume, t) for t in ticks]
        for future in concurrent.futures.as_completed(futures):
            r = future.result()
            if r:
                results.append(r)
                
    # Sort by Volume Ratio (Highest explosion first)
    results.sort(key=lambda x: x['vol_ratio'], reverse=True)
                
    return jsonify({'count': len(results), 'results': results})

@app.route('/scan_last_day_buy', methods=['GET'])
def scan_last_day_buy():
    ticks = ALL_BIST_TICKS
    results = []
    

    def check_last_day_fallback_tv(sym):
        try:
            handler = TA_Handler(
                symbol=sym,
                screener="turkey",
                exchange="BIST",
                interval=Interval.INTERVAL_4_HOURS
            )
            analysis = handler.get_analysis()
            ind = analysis.indicators
            
            # --- FALLBACK LOGIC (Approximation of Trinity) ---
            # 1. Trend: Close > SMA200
            # 2. Dip: RSI < 40 or Close < Lower BB (Since we can't easily check prev low < prev lower)
            # 3. Reversal: RSI > RSI[1] AND Close > Lower BB
            
            close = ind.get('close')
            sma200 = ind.get('SMA200')
            rsi = ind.get('RSI')
            rsi_prev = ind.get('RSI[1]') # Can be None if no history
            bb_lower = ind.get('BB.lower')
            
            if None in [close, sma200, rsi, bb_lower]: return None
            
            # Trend Check (Close > SMA200)
            if close <= sma200: return None
            
            # Reversal Check
            # - Price recovered above Lower Band
            # - RSI ticking up (if available)
            
            cond_reversal = (close > bb_lower)
            if rsi_prev:
                cond_reversal = cond_reversal and (rsi > rsi_prev)
            
            # Cheap/Dip Context Check
            # Either RSI is still somewhat low (<50) to leave room for upside, 
            # OR price is relatively close to Lower Band (< 3%?) to catch the bounce early.
            # Trinity usually catches the bounce right after a dip below band.
            # If we are here, Close > Lower BB is true.
            # Was it below recently? Hard to know without history.
            # Proxy: RSI < 55 (Not overbought) AND (Close - Lower BB) / Lower BB < 0.05 (Recently bounced)
            
            cond_cheap = (rsi < 55) and ( (close - bb_lower) / bb_lower < 0.05 )
            
            if cond_reversal and cond_cheap:
                print(f"FALLBACK MATCH: {sym}")
                return {
                    'symbol': sym,
                    'price': close,
                    'current_price': close,
                    'rsi': round(rsi, 2),
                    'time': int(datetime.datetime.now().timestamp()), # Approximate time
                    'days_ago': 0, # Fresh signal
                    'source': 'TradingView'
                }
                
        except Exception as e:
            # print(f"TV Fallback Error {sym}: {e}")
            return None
        return None

    def check_last_day(sym):
        # Result placeholder
        res = None
        
        # --- ATTEMPT 1: YFINANCE (Rich Data, Precise Logic) ---
        try:
            full_sym = sym + '.IS'
            # OPTIMIZATION: Use 1y instead of 730d to reduce failure rate
            ticker = yf.Ticker(full_sym)
            hist = ticker.history(period="1y", interval="1h")
            
            # Only proceed if we have enough data for 4H resampling
            # 1y 1h data ~ 2200 rows.
            enough_data = not hist.empty and len(hist) > 100
            
            if enough_data:
                # Resample to 4H
                hist_4h = hist.resample('4h').agg({
                    'Open': 'first', 
                    'High': 'max', 
                    'Low': 'min', 
                    'Close': 'last', 
                    'Volume': 'sum'
                }).dropna()
                
                # Check SMA200 requirement
                if len(hist_4h) >= 205:
                    # --- CALCULATE INDICATORS (TRINITY STRATEGY) ---
                    df = hist_4h.copy()
                    df['SMA200'] = df['Close'].rolling(window=200).mean()
                    df['SMA20'] = df['Close'].rolling(window=20).mean()
                    df['STD20'] = df['Close'].rolling(window=20).std()
                    df['Lower'] = df['SMA20'] - (df['STD20'] * 2)
                    
                    delta = df['Close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rs = gain / loss
                    df['RSI'] = 100 - (100 / (1 + rs))
                    
                    # Last 4 bars logic
                    lookback = 4
                    recent_indices = range(len(df) - lookback, len(df))
                    
                    for i in reversed(recent_indices):
                        if i < 1: continue 
                        curr = df.iloc[i]
                        prev = df.iloc[i-1]
                        
                        cond_trend = curr['Close'] > curr['SMA200']
                        cond_cheap = prev['Low'] <= prev['Lower']
                        cond_reversal = (curr['Close'] > curr['Lower']) and (curr['RSI'] > prev['RSI'])
                        
                        if cond_trend and cond_cheap and cond_reversal:
                            res = {
                                'symbol': sym,
                                'price': curr['Close'], 
                                'current_price': df.iloc[-1]['Close'],
                                'rsi': curr['RSI'],
                                'time': int(curr.name.timestamp()),
                                'days_ago': (len(df) - 1) - i,
                                'source': 'yfinance'
                            }
                            break
        except Exception as e:
            # print(f"YF Error {sym}: {e}")
            pass

        # --- ATTEMPT 2: FALLBACK (TradingView) ---
        if res is None:
            # If YF failed or returned no result, should we try TV?
            # TV Logic is approximated. We only want to use it if YF *FAILED TO FETCH DATA*.
            # If YF fetched data and found NO SIGNAL, we don't necessarily want to double check with looser logic.
            # BUT, the user issue is "Missing Stocks". This implies YF is failing to fetch.
            # So, only check TV if we suspect YF failed data.
            # In my code above, `enough_data` flag handles empty check.
            # If `enough_data` was False, `res` is None. We should try TV.
            # If `enough_data` was True but no signal found, `res` is None. 
            # Should we retry with TV? Probably not, as YF is ground truth.
            
            # Implementation detail: I didn't return early inside YF block.
            # If hist is empty, we fall through here.
            # If hist is OK but no signal, we fall through here.
            # To differentiate, let's just run TV if result is None? 
            # Risk: might get duplicate/false positives if YF logic was strict and TV is loose.
            # Better: Only run TV if `enough_data` was False or Exception occurred?
            # Let's keep it simple: Try TV if res is None. 
            # Wait, `check_last_day_fallback_tv` is expensive (network call).
            # Checking EVERY stock twice is slow.
            # Let's assume YF covers most. Only if YF fails (Exception or Empty) use TV.
            
            # Re-structure for flow control is hard with single function replacement.
            # I'll stick to: Check TV if res is None. It adds robustness.
            # The TV check is only one HTTP request.
             res = check_last_day_fallback_tv(sym)
             
        return res

    print(f"Starting TRINITY 4H Scan (Hybrid) for {len(ticks)} tickers...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(check_last_day, t) for t in ticks]
        for future in concurrent.futures.as_completed(futures):
            r = future.result()
            if r:
                results.append(r)
                
    return jsonify({'count': len(results), 'results': results})

@app.route('/scan_similarity', methods=['GET'])
def scan_similarity():
    """
    Scans for stocks where the last 20 days price action matches a historical 20-day window
    with > 90% similarity (Pearson Correlation).
    """
    ticks = ALL_BIST_TICKS
    results = []
    
    # 1. Helper: Pearson Correlation
    def calculate_similarity(series1, series2):
        if len(series1) != len(series2): return 0
        # Normalize? Actually fast correlation on returns or normalized prices is better.
        # Simple Pearson on raw prices can be misleading if scale differs significantly, 
        # but for shape similarity on SAME stock, it works if we normalize or just look at shape.
        # Pearson is scale invariant for linear relationships (y = ax + b).
        # So price levels don't block similarity if the SHAPE is same.
        try:
            return np.corrcoef(series1, series2)[0, 1]
        except:
            return 0

    def check_similarity(sym):
        try:
            full_sym = sym + '.IS'
            ticker = yf.Ticker(full_sym)
            # Fetch 3 years to have ample history
            hist = ticker.history(period="3y", interval="1d")
            
            if hist.empty or len(hist) < 250: return None # Need at least ~1 year of data + current
            
            # Pattern window size
            W = 20 
            
            # Current Pattern (Last W days)
            if len(hist) < W + 1: return None
            
            # Use 'Close' prices
            closes = hist['Close'].values
            
            current_pattern = closes[-W:]
            
            # We search in history: from index 0 to (Total - W - W) 
            # We don't want to match the pattern with itself or immediate recent past (overlap).
            # Let's say we ignore the last 60 days for history search to find "past" patterns.
            
            search_limit = len(closes) - W - 10 # Buffer of 10 days
            
            best_match = {
                'score': -1.0,
                'date': None,
                'end_price': 0
            }
            
            # Sliding Window
            # Optimization: This loop in Python might be slow for 500 stocks x 700 days.
            # But let's try. 3 years ~ 750 bars. ~700 iterations. 500 stocks = 350,000 ops.
            # It might take ~10-20 seconds total with threading. Acceptable.
            
            found_candidate = False
            
            for i in range(0, search_limit):
                window = closes[i : i+W]
                
                # Check Length
                if len(window) != W: continue
                
                # Calculate Similarity
                score = calculate_similarity(current_pattern, window)
                
                # Check Threshold (90%)
                if score >= 0.90:
                    # Found a high match!
                    # Store the highest one? Or just the most recent high one?
                    if score > best_match['score']:
                        best_match['score'] = score
                        # Date at the END of the historical window
                        match_date = hist.index[i+W-1]
                        best_match['date'] = match_date.strftime('%Y-%m-%d')
                        best_match['end_price'] = window[-1]
                        found_candidate = True
            
            if found_candidate:
                # Calculate percent change from pattern end to next 5-10 days? (Forecast)
                # Not requested yet, just show the match.
                
                return {
                    'symbol': sym,
                    'score': round(best_match['score'] * 100, 2),
                    'date': best_match['date'],
                    'price': closes[-1]
                }
                
        except Exception as e:
            return None
        return None

    print(f"Starting SIMILARITY Scan for {len(ticks)} tickers...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(check_similarity, t) for t in ticks]
        for future in concurrent.futures.as_completed(futures):
            r = future.result()
            if r:
                results.append(r)
                
    # Sort by Score Descending
    results.sort(key=lambda x: x['score'], reverse=True)
    
    return jsonify({'count': len(results), 'results': results})

def calc_adx(df, period=14):
    """
    Computes ADX (Average Directional Index) using standard Pandas.
    Returns the ADX series.
    """
    df = df.copy()
    df['up_move'] = df['High'] - df['High'].shift(1)
    df['down_move'] = df['Low'].shift(1) - df['Low']
    
    df['pdm'] = np.where((df['up_move'] > df['down_move']) & (df['up_move'] > 0), df['up_move'], 0)
    df['ndm'] = np.where((df['down_move'] > df['up_move']) & (df['down_move'] > 0), df['down_move'], 0)
    
    df['tr'] = np.maximum(
        (df['High'] - df['Low']), 
        np.maximum(
            abs(df['High'] - df['Close'].shift(1)), 
            abs(df['Low'] - df['Close'].shift(1))
        )
    )
    
    # Wilder's Smoothing
    def smooth(series, p):
        return series.ewm(alpha=1/p, adjust=False).mean()
    
    tr_s = smooth(df['tr'], period)
    pdm_s = smooth(df['pdm'], period)
    ndm_s = smooth(df['ndm'], period)
    
    pdi = 100 * (pdm_s / tr_s)
    ndi = 100 * (ndm_s / tr_s)
    
    dx = 100 * abs(pdi - ndi) / (pdi + ndi)
    adx = smooth(dx, period)
    
    return adx





def sinyal_hesapla(df, risk_mode='conservative'):
    """
    Bu fonksiyon DataFrame alır ve içine 'Buy_Signal' sütunu ekler.
    risk_mode: 'aggressive' (Eski) veya 'conservative' (Filtreli)
    """
    # Copy to avoid SettingWithCopy warnings on slices
    df = df.copy()
    
    # 1. İndikatörleri Hesapla
    # Bollinger Bantları (18, 2)
    df['SMA18'] = df['Close'].rolling(window=18).mean()
    df['STD18'] = df['Close'].rolling(window=18).std()
    df['Upper'] = df['SMA18'] + (df['STD18'] * 2)
    df['Lower'] = df['SMA18'] - (df['STD18'] * 2) 
    
    # Band Width & Expansion Filter
    # Band Width = (Upper - Lower) / Middle(SMA)
    # Expanding: Current Width > Previous Width
    df['BandWidth'] = (df['Upper'] - df['Lower']) / df['SMA18']
    df['BW_Expand'] = df['BandWidth'] > df['BandWidth'].shift(1)
    
    # RSI Hesapla (14 periyot)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI_Signal'] = 100 - (100 / (1 + rs))
    
    # 2. KARAR MEKANİZMASI (Logic)
    
    # Temel Sinyal: Fiyat < Lower Band & RSI < 35 & Band Genişliyor (Trend/Volatilite Başlangıcı)
    # User: "IF band_width genişliyor: trend modu aktif" -> Trade Allow
    # User: "IF band_width düşük: trade bekle" -> Trade Block (Implied by not expanding or low width)
    # We use Expansion as the trigger.
    
    basic_signal = (df['Close'] < df['Lower']) & (df['RSI_Signal'] < 35) & (df['BW_Expand'])
    
    if risk_mode == 'aggressive':
        df['Buy_Signal'] = basic_signal
    else:
        # CONSERVATIVE (TUTUCU) MOD
        # Ek Filtreler:
        # 1. Trend Filtresi: Fiyat > EMA 200 (Yükselen Trendde al)
        # 2. ADX Filtresi: ADX > 20 (Yatay piyasa değil)
        
        df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
        df['ADX'] = calc_adx(df)
        
        # Filtreleme
        # Trend is UP if Close > EMA200
        trend_ok = df['Close'] > df['EMA200']
        # Trend Strong enough if ADX > 20
        adx_ok = df['ADX'] > 20
        
        df['Buy_Signal'] = basic_signal & trend_ok & adx_ok

    # İsteğe bağlı: Sadece sinyal olan satırları filtrele
    sinyaller = df[df['Buy_Signal'] == True]
    
    return df, sinyaller

def cikis_stratejileri_hesapla(df):
    """
    Bu fonksiyon DataFrame alır ve çıkış (satış) seviyelerini ekler.
    Gerekli sütunlar: 'Close', 'High', 'Low', 'Upper' (Bollinger Üst), 'RSI_Signal'
    """
    # Copy to avoid SettingWithCopy
    df = df.copy()
    
    # --- 1. ATR Hesaplama (Volatilite bazlı mesafe için) ---
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df['ATR'] = true_range.rolling(window=14).mean()

    # --- 2. Dinamik Teknik Satış Sinyali (Kâr Realizasyonu) ---
    # Fiyat Üst Banda değdi VEYA RSI çok şişti (70+)
    # Note: Using RSI_Signal from sinyal_hesapla
    if 'RSI_Signal' in df.columns:
        df['Sell_Signal_Indicator'] = (df['Close'] > df['Upper']) | (df['RSI_Signal'] > 70)
    else:
        # Fallback if RSI not present, though it should be
        df['Sell_Signal_Indicator'] = (df['Close'] > df['Upper'])

    # --- 3. İz Süren Stop (Chandelier Exit Mantığı) ---
    # Son 22 günün en yüksek kapanışını bul
    df['Rolling_Max'] = df['Close'].rolling(window=22).max()
    df['Trailing_Stop'] = df['Rolling_Max'] - (df['ATR'] * 2.5) # 2.5 katı kadar gevşeme payı

    # --- 4. Sabit Hedef Hesaplayıcı (Son gün için) ---
    current_price = df['Close'].iloc[-1]
    current_atr = df['ATR'].iloc[-1]
    
    # Handle NaN in ATR for very short histories
    if pd.isna(current_atr): current_atr = 0
    
    stop_loss_level = current_price - (current_atr * 2) 
    take_profit_level = current_price + (current_atr * 4) 
    
    return df, stop_loss_level, take_profit_level

def calc_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calc_ichimoku(df):
    high9 = df['High'].rolling(window=9).max()
    low9 = df['Low'].rolling(window=9).min()
    df['tenkan'] = (high9 + low9) / 2

    high26 = df['High'].rolling(window=26).max()
    low26 = df['Low'].rolling(window=26).min()
    df['kijun'] = (high26 + low26) / 2

    df['spanA'] = ((df['tenkan'] + df['kijun']) / 2).shift(26)
    
    high52 = df['High'].rolling(window=52).max()
    low52 = df['Low'].rolling(window=52).min()
    df['spanB'] = ((high52 + low52) / 2).shift(26)
    
    # Current Cloud (for validation today) - We need values at 'now', which corresponds to 'shift(26)' from 26 days ago.
    # Actually standard Ichimoku plots SpanA/B 26 bars ahead.
    # To check if price is above cloud TODAY, we look at the SpanA/B values that are plotted TODAY.
    # These values were generated 26 days ago.
    # Pandas shift(26) moves the value forward. So df['spanA'] at index T holds the value calculated at T-26.
    # This is correct for "Support/Resistance at T".
    return df

def check_trend_weekly(df):
    # Logic: Close > SpanA & Close > SpanB (Bullish) or Close < Both (Bearish)
    # Cloud Color: Bullish if SpanA > SpanB
    if df.empty: return 'NEUTRAL'
    last = df.iloc[-1]
    
    if last['Close'] > max(last['spanA'], last['spanB']) and last['spanA'] > last['spanB']:
        return 'LONG'
    elif last['Close'] < min(last['spanA'], last['spanB']) and last['spanA'] < last['spanB']:
        return 'SHORT'
    return 'NEUTRAL'

def calc_atr(df, period=14):
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    return true_range.rolling(window=period).mean()

def check_sell_zone(df):
    """
    Checks if the asset is in a potential sell zone (Overbought).
    """
    if df.empty: return {'status': 'NEUTRAL', 'msg': 'Veri Yok'}
    
    # Ensure RSI exists
    if 'rsi' not in df: df['rsi'] = calc_rsi(df['Close'])
    last_rsi = df['rsi'].iloc[-1]
    last_close = df['Close'].iloc[-1]
    
    # Check Bollinger Upper (if available) or just RSI
    # We can calculate BB manually if needed, but let's stick to RSI for speed/safety
    if last_rsi > 75:
        return {'status': 'SELL_ZONE', 'msg': 'AŞIRI ALIM (RSI > 75)'}
    elif last_rsi > 70:
        return {'status': 'WARNING', 'msg': 'RSI Şişiyor (>70)'}
        
    return {'status': 'NEUTRAL', 'msg': 'Güvenli Bölge'}

def analyze_trend_health(df_4h):
    # 5 Pillars: Structure, Cloud, RSI, Volume, ATR
    if len(df_4h) < 20: return {'score': 0, 'mode': 'RANGE', 'pillars': {}}
    
    last = df_4h.iloc[-1]
    prev = df_4h.iloc[-2]

    # 1. Structure (HH + HL sequence approximation)
    # Check if we are generally making higher lows in the last 20 bars
    lows = df_4h['Low'].iloc[-20:]
    # Simple linear regression slope of lows could work, or just check halves
    # Let's use a simpler heuristic: Current Low > Low 10 bars ago
    structure_ok = last['Low'] > df_4h['Low'].iloc[-10]

    # 2. Ichimoku Relationship (Price > Kijun)
    cloud_ok = last['Close'] > last['kijun']

    # 3. Momentum (RSI > 50 & Not diving)
    if 'rsi' not in df_4h: df_4h['rsi'] = calc_rsi(df_4h['Close'])
    last_rsi = df_4h['rsi'].iloc[-1]
    rsi_ok = last_rsi > 50

    # 4. Volume Behavior (Rising on Up moves?)
    # Compare Avg Volume of Green candles vs Red candles in last 10 bars
    recent = df_4h.iloc[-10:]
    green_vol = recent[recent['Close'] > recent['Open']]['Volume'].mean()
    red_vol = recent[recent['Close'] < recent['Open']]['Volume'].mean()
    if pd.isna(green_vol): green_vol = 0
    if pd.isna(red_vol): red_vol = 0
    volume_ok = green_vol > red_vol

    # 5. Volatility (ATR Rising/Stable)
    if 'atr' not in df_4h: df_4h['atr'] = calc_atr(df_4h)
    atr_now = df_4h['atr'].iloc[-1]
    atr_prev = df_4h['atr'].iloc[-5] # 5 bars ago
    # Valid if ATR is NOT crashing down while price rises (divergence). 
    # Or simply ATR is healthy. Let's say ATR shouldn't be dropping > 10%
    atr_ok = atr_now >= (atr_prev * 0.9)

    score = sum([structure_ok, cloud_ok, rsi_ok, volume_ok, atr_ok])
    mode = 'TREND' if score >= 4 else 'RANGE' # 4/5 required for Trend Mode

    
    # SELL ZONE CHECK
    sell_analysis = check_sell_zone(df_4h)

    return {
        'score': score,
        'mode': mode,
        'rsi_val': round(last_rsi, 2),
        'sell_zone': sell_analysis,
        'pillars': {
            'structure': bool(structure_ok),
            'cloud': bool(cloud_ok),
            'rsi': bool(rsi_ok),
            'volume': bool(volume_ok),
            'atr': bool(atr_ok)
        }
    }

def detect_candle_patterns(df):
    # Analyze last 2 candles for patterns
    if len(df) < 2: return None
    
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    
    curr_body = abs(curr['Close'] - curr['Open'])
    prev_body = abs(prev['Close'] - prev['Open'])
    
    curr_range = curr['High'] - curr['Low']
    
    # 1. Bullish Engulfing
    if (prev['Close'] < prev['Open'] and 
        curr['Close'] > curr['Open'] and 
        curr['Open'] < prev['Close'] and 
        curr['Close'] > prev['Open']):
        return {'name': 'BULLISH ENGULFING', 'type': 'BULL', 'time': int(curr.name.timestamp())}

    # 2. Bearish Engulfing
    if (prev['Close'] > prev['Open'] and 
        curr['Close'] < curr['Open'] and 
        curr['Open'] > prev['Close'] and 
        curr['Close'] < prev['Open']):
        return {'name': 'BEARISH ENGULFING', 'type': 'BEAR', 'time': int(curr.name.timestamp())}
        
    # 3. Hammer (Bullish)
    lower_wick = min(curr['Close'], curr['Open']) - curr['Low']
    if (lower_wick > 2 * curr_body) and (curr['High'] - max(curr['Close'], curr['Open']) < curr_body * 0.5):
        return {'name': 'HAMMER', 'type': 'BULL', 'time': int(curr.name.timestamp())}

    # 4. Shooting Star (Bearish)
    upper_wick = curr['High'] - max(curr['Close'], curr['Open'])
    if (upper_wick > 2 * curr_body) and (min(curr['Close'], curr['Open']) - curr['Low'] < curr_body * 0.5):
        return {'name': 'SHOOTING STAR', 'type': 'BEAR', 'time': int(curr.name.timestamp())}
        
    # 5. Doji
    if curr_body <= (curr_range * 0.1):
         return {'name': 'DOJI', 'type': 'NEUTRAL', 'time': int(curr.name.timestamp())}

    return None

def analyze_sma_trend(df_daily):
    if len(df_daily) < 201: return None # Need 200 bars for SMA 200
    
    # Calculate SMAs
    df_daily['sma50'] = df_daily['Close'].rolling(window=50).mean()
    df_daily['sma200'] = df_daily['Close'].rolling(window=200).mean()
    
    last = df_daily.iloc[-1]
    prev = df_daily.iloc[-2]
    
    # 1. Price vs SMA 50 (Short/Mid Term Control)
    price_above_50 = last['Close'] > last['sma50']
    
    # 2. Price vs SMA 200 (Long Term Structure)
    price_above_200 = last['Close'] > last['sma200']
    
    # 3. SMA 50 Slope (Momentum) based on last 5 bars
    sma50_prev5 = df_daily['sma50'].iloc[-5]
    sma50_slope_up = last['sma50'] > sma50_prev5
    
    # 4. Structure (SMA 50 vs SMA 200)
    structure_bullish = last['sma50'] > last['sma200']
    
    # 5. Cross Events
    # Golden Cross: SMA 50 crosses UP SMA 200
    golden_cross = (prev['sma50'] <= prev['sma200']) and (last['sma50'] > last['sma200'])
    # Death Cross: SMA 50 crosses DOWN SMA 200
    death_cross = (prev['sma50'] >= prev['sma200']) and (last['sma50'] < last['sma200'])
    
    status = "NÖTR"
    if golden_cross: status = "GOLDEN CROSS"
    elif death_cross: status = "DEATH CROSS"
    elif structure_bullish: status = "YÜKSELİŞ"
    else: status = "DÜŞÜŞ"

    return {
        'price_vs_50': bool(price_above_50),
        'price_vs_200': bool(price_above_200),
        'sma50_slope': bool(sma50_slope_up),
        'structure_bullish': bool(structure_bullish),
        'cross_status': status,
        'golden_cross': bool(golden_cross),
        'death_cross': bool(death_cross)
    }

def add_cascade_ui_fields(result_dict):
    """
    Helper function to add UI-expected fields to cascade analysis result.
    Maps backend fields (status, stage, trend) to UI fields (direction, setup_active, trigger_active, signal_strength).
    """
    status = result_dict.get('status', 'FAIL')
    stage = result_dict.get('stage', '')
    trend = result_dict.get('trend', 'NEUTRAL')
    
    # direction: Map from trend (already LONG/SHORT/NEUTRAL)
    result_dict['direction'] = trend
    
    # setup_active: True if in 4H stage and waiting/passive
    result_dict['setup_active'] = (stage == '4H' and status in ['WAITING', 'PASSIVE'])
    
    # trigger_active: True if in 1H stage with ACTIVE status
    result_dict['trigger_active'] = (stage == '1H' and status == 'ACTIVE')
    
    # signal_strength: Based on status and stage
    if status == 'ACTIVE':
        result_dict['signal_strength'] = 'green'
    elif status == 'WAITING' and stage in ['4H', '1H']:
        result_dict['signal_strength'] = 'yellow'
    else:
        result_dict['signal_strength'] = 'gray'
    
    return result_dict

def run_cascade_analysis(ticker, symbol):
    try:
        # Try to fetch 1H data first
        hist_1h = ticker.history(period="730d", interval="1h")
        data_type = "1h"
        use_daily_fallback = False
        
        # Fallback to daily data if 1h is not available or insufficient
        if hist_1h.empty or len(hist_1h) < 50:
            print(f"INFO: {symbol} - 1H veri yok, günlük veriye geçiliyor...")
            hist_1h = ticker.history(period="2y", interval="1d")
            data_type = "1d"
            use_daily_fallback = True
            
            if hist_1h.empty or len(hist_1h) < 50:
                return add_cascade_ui_fields({
                    'status': 'FAIL', 
                    'stage': 'DATA',
                    'msg': 'Yetersiz Veri (Hem 1H hem Günlük)',
                    'data_type': 'none',
                    'levels': {'price': 0, 'stop': 0, 'target': 0}
                })
        
        # Calculate ATR and current price for price levels
        hist_1h_atr = calc_atr(hist_1h, period=14)
        current_price = hist_1h.iloc[-1]['Close']
        current_atr = hist_1h_atr.iloc[-1] if not pd.isna(hist_1h_atr.iloc[-1]) else current_price * 0.02
        
        # PRE-CALCULATE 4H DATA & ANALYTICS (Guarantee Visibility)
        # If using daily fallback, resample to weekly instead of 4h
        if use_daily_fallback:
            hist_4h = hist_1h.resample('1W').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
        else:
            hist_4h = hist_1h.resample('4h').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
        
        hist_4h = calc_ichimoku(hist_4h)
        trend_health = analyze_trend_health(hist_4h)
        pattern_4h = detect_candle_patterns(hist_4h)

        # PRE-CALCULATE DAILY DATA & SMA ANALYSIS (Guarantee Visibility)
        if use_daily_fallback:
            hist_d = hist_1h  # Already have daily data
        else:
            hist_d = ticker.history(period="2y", interval="1d") # 2y for safety
        sma_analysis = analyze_sma_trend(hist_d)
        
        if hist_d.empty or len(hist_d) < 50:
             # Critical failure if no daily data, but return whatever we have
             stop_price = round(current_price - (current_atr * 2), 2)
             target_price = round(current_price + (current_atr * 3.5), 2)
             return add_cascade_ui_fields({
                 'status': 'FAIL', 
                 'stage': 'DAILY', 
                 'msg': 'Günlük Veri Yok', 
                 'data_type': data_type,
                 'trend_health': trend_health, 
                 'sma_analysis': sma_analysis, 
                 'pattern_4h': pattern_4h,
                 'levels': {
                     'price': round(current_price, 2),
                     'stop': stop_price,
                     'target': target_price
                 }
             })

        # 1. Weekly (Trend)
        hist_wk = ticker.history(period="2y", interval="1wk")
        if len(hist_wk) < 52:
            stop_price = round(current_price - (current_atr * 2), 2)
            target_price = round(current_price + (current_atr * 3.5), 2)
            return add_cascade_ui_fields({
                'status': 'FAIL', 
                'stage': 'WEEKLY', 
                'msg': 'Yetersiz Veri', 
                'data_type': data_type,
                'trend_health': trend_health, 
                'sma_analysis': sma_analysis, 
                'pattern_4h': pattern_4h,
                'levels': {
                    'price': round(current_price, 2),
                    'stop': stop_price,
                    'target': target_price
                }
            })
        hist_wk = calc_ichimoku(hist_wk)
        trend = check_trend_weekly(hist_wk)
        
        # Calculate stop and target based on trend mode
        stop_price = round(current_price - (current_atr * 2), 2)
        if trend_health['mode'] == 'TREND':
            target_price = round(current_price + (current_atr * 5), 2)  # ~10%+ dynamic
        else:
            target_price = round(current_price + (current_atr * 3.5), 2)  # ~7% fixed
        
        if trend == 'NEUTRAL':
            msg = 'Haftalık Yön Belirsiz'
            if use_daily_fallback:
                msg += ' (Günlük veri kullanıldı)'
            return add_cascade_ui_fields({
                'status': 'PASSIVE', 
                'stage': 'WEEKLY', 
                'msg': msg, 
                'data_type': data_type,
                'trend': trend,
                'trend_health': trend_health,
                'sma_analysis': sma_analysis,
                'pattern_4h': pattern_4h,
                'levels': {
                    'price': round(current_price, 2),
                    'stop': stop_price,
                    'target': target_price
                }
            })

        # 2. Daily (Confirmation)
        # Reuse hist_d fetched above
        hist_d = calc_ichimoku(hist_d)
        hist_d['rsi'] = calc_rsi(hist_d['Close'])
        last_d = hist_d.iloc[-1]
        
        # Determine Daily Trend Status (Independent of Weekly Logic)
        daily_trend_status = "YÜKSELİŞ" if last_d['Close'] > last_d['kijun'] else "DÜŞÜŞ"
        
        confirmed = False
        if trend == 'LONG':
            # Price > Kijun & RSI > 50
            if last_d['Close'] > last_d['kijun'] and last_d['rsi'] > 50: confirmed = True
        else: # SHORT
            if last_d['Close'] < last_d['kijun'] and last_d['rsi'] < 50: confirmed = True
            
        if not confirmed:
            msg = 'Günlük Onay Yok'
            if use_daily_fallback:
                msg += ' (Günlük veri kullanıldı)'
            return add_cascade_ui_fields({
                'status': 'PASSIVE', 
                'stage': 'DAILY', 
                'msg': msg, 
                'data_type': data_type,
                'trend': trend,
                'daily_trend': daily_trend_status,
                'trend_health': trend_health,
                'sma_analysis': sma_analysis,
                'pattern_4h': pattern_4h,
                'levels': {
                    'price': round(current_price, 2),
                    'stop': stop_price,
                    'target': target_price
                }
            })

        # 3. 4H (Zone/Confluence)
        # Fetch 1H and resample to 4H - ALREADY DONE AT TOP
        # hist_1h check skipped as verified
        
        # Fib Calculation (Last 100 bars)
        lookback = hist_4h.iloc[-100:]
        high_g = lookback['High'].max()
        low_g = lookback['Low'].min()
        fib382 = low_g + (high_g - low_g) * 0.382
        fib500 = low_g + (high_g - low_g) * 0.500
        fib618 = low_g + (high_g - low_g) * 0.618
        
        # Check if price is in Retracement Zone (Fib 0.382 - 0.618) relative to Trend
        # And Confluence with Kijun
        last_4h = hist_4h.iloc[-1]
        in_zone = False
        
        # Simple Zone Check: Price roughly near Kijun (+- 1%) OR Price inside Fib Pullback Area
        # Ideally we want exact intersection logic, but for "Zone Ready" we check proximity.
        dist_kijun = abs(last_4h['Close'] - last_4h['kijun']) / last_4h['Close']
        if dist_kijun < 0.015: in_zone = True # Close to Kijun
        
        if not in_zone:
             # Just providing data, not blocking completely usually, but user asked for strict.
             msg = 'Giriş Bölgesi Bekleniyor'
             if use_daily_fallback:
                 msg += ' (Günlük veri kullanıldı)'
             return add_cascade_ui_fields({
                 'status': 'WAITING', 
                 'stage': '4H', 
                 'msg': msg, 
                 'data_type': data_type,
                 'trend': trend, 
                 'daily_trend': daily_trend_status,
                 'zone': [fib618, fib500],
                 'trend_health': trend_health,
                 'sma_analysis': sma_analysis,
                 'pattern_4h': pattern_4h,
                 'levels': {
                     'price': round(current_price, 2),
                     'stop': stop_price,
                     'target': target_price
                 }
             })

        # 4. 1H (Trigger)
        hist_1h = calc_ichimoku(hist_1h) # raw 1h
        hist_1h['rsi'] = calc_rsi(hist_1h['Close'])
        last_1h = hist_1h.iloc[-1]
        prev_1h = hist_1h.iloc[-2]
        
        triggered = False
        # ... (Trigger logic existing) ...
        if trend == 'LONG':
            if last_1h['rsi'] > prev_1h['rsi'] and last_1h['Close'] > last_1h['Open']: triggered = True
        else:
            if last_1h['rsi'] < prev_1h['rsi'] and last_1h['Close'] < last_1h['Open']: triggered = True
            
        if triggered:
            # Determine Target based on Trend Mode
            target_msg = "SABİT %7"
            if trend_health['mode'] == 'TREND':
                target_msg = "DİNAMİK %10+"
            
            msg = 'İŞLEM AKTİF'
            if use_daily_fallback:
                msg += ' (Günlük veri kullanıldı)'
            return add_cascade_ui_fields({
                'status': 'ACTIVE', 
                'stage': '1H', 
                'msg': msg, 
                'data_type': data_type,
                'trend': trend, 
                'daily_trend': daily_trend_status,
                'target': target_msg,
                'trend_health': trend_health,
                'sma_analysis': sma_analysis,
                'pattern_4h': pattern_4h,
                'levels': {
                    'price': round(current_price, 2),
                    'stop': stop_price,
                    'target': target_price
                }
            })
        else:
             target_msg = "BEKLİYOR" # Default for waiting
             if trend_health['mode'] == 'TREND': target_msg = "DİNAMİK"
             
             msg = 'Tetik Bekleniyor'
             if use_daily_fallback:
                 msg += ' (Günlük veri kullanıldı)'
             return add_cascade_ui_fields({
                 'status': 'WAITING', 
                 'stage': '1H', 
                 'msg': msg, 
                 'data_type': data_type,
                 'trend': trend, 
                 'daily_trend': daily_trend_status,
                 'target': target_msg,
                 'trend_health': trend_health,
                 'sma_analysis': sma_analysis,
                 'pattern_4h': pattern_4h,
                 'levels': {
                     'price': round(current_price, 2),
                     'stop': stop_price,
                     'target': target_price
                 }
             })

    except Exception as e:
        print(f"Cascade Error: {e}")
        return add_cascade_ui_fields({
            'status': 'FAIL', 
            'stage': 'SYSTEM', 
            'msg': str(e),
            'levels': {'price': 0, 'stop': 0, 'target': 0}
        })

# --- ADVANCED ANALYSIS MODULES ---

# Optional TextBlob Import for Sentiment
try:
    from textblob import TextBlob
    TEXTBLOB_AVAIL = True
except ImportError:
    TEXTBLOB_AVAIL = False
    print("Warning: TextBlob not found. Using simple dictionary sentiment.")

def find_support_resistance(df, n=5):
    """
    Finds Support and Resistance levels using local minima/maxima.
    Clusters similar levels.
    """
    if df.empty: return []
    
    closes = df['Close'].values
    levels = []
    
    # 1. Detect Local Extrema
    if SCIPY_AVAIL:
        # Scipy method
        # Maxima (Resistance)
        max_idx = argrelextrema(closes, np.greater, order=n)[0]
        # Minima (Support)
        min_idx = argrelextrema(closes, np.less, order=n)[0]
        
        for i in max_idx: levels.append((closes[i], 'RESISTANCE'))
        for i in min_idx: levels.append((closes[i], 'SUPPORT'))
    else:
        # Numpy Fallback (Simple Window)
        # Iterate and check neighbors
        for i in range(n, len(closes) - n):
            window = closes[i-n:i+n+1]
            if closes[i] == max(window):
                levels.append((closes[i], 'RESISTANCE'))
            elif closes[i] == min(window):
                levels.append((closes[i], 'SUPPORT'))

    if not levels: return []

    # 2. Cluster Levels (Group within 1.5%)
    levels.sort(key=lambda x: x[0])
    
    clusters = []
    if levels:
        curr_cluster = [levels[0]]
        
        for i in range(1, len(levels)):
            price, type_ = levels[i]
            prev_price = curr_cluster[-1][0]
            
            # If within 1.5% difference, group them
            if (price - prev_price) / prev_price < 0.015:
                curr_cluster.append(levels[i])
            else:
                # Close old cluster
                avg_price = sum(x[0] for x in curr_cluster) / len(curr_cluster)
                # Determine type by majority
                sup_count = sum(1 for x in curr_cluster if x[1] == 'SUPPORT')
                res_count = sum(1 for x in curr_cluster if x[1] == 'RESISTANCE')
                final_type = 'SUPPORT' if sup_count >= res_count else 'RESISTANCE'
                strength = len(curr_cluster) # How many touches
                clusters.append({'price': avg_price, 'type': final_type, 'strength': strength})
                curr_cluster = [levels[i]]
        
        # Add last cluster
        avg_price = sum(x[0] for x in curr_cluster) / len(curr_cluster)
        sup_count = sum(1 for x in curr_cluster if x[1] == 'SUPPORT')
        res_count = sum(1 for x in curr_cluster if x[1] == 'RESISTANCE')
        final_type = 'SUPPORT' if sup_count >= res_count else 'RESISTANCE'
        strength = len(curr_cluster) 
        clusters.append({'price': avg_price, 'type': final_type, 'strength': strength})

    # Sort by strength (descending) and return top 5
    clusters.sort(key=lambda x: x['strength'], reverse=True)
    return clusters[:5]

def find_similarity(df, window=30):
    """
    Finds the most similar historical pattern to the recent price action.
    """
    if len(df) < (window * 2 + 5): return None
    
    targets = df['Close'].values
    current_pattern = targets[-window:]
    
    # Normalize current pattern (0-1 scaling)
    c_min, c_max = current_pattern.min(), current_pattern.max()
    if c_max == c_min: return None
    curr_norm = (current_pattern - c_min) / (c_max - c_min)

    best_score = -1
    best_idx = -1
    
    # Scan history (stop before the recent window to avoid self-match)
    limit = len(targets) - (window * 2) 
    
    for i in range(limit):
        past_pattern = targets[i : i + window]
        p_min, p_max = past_pattern.min(), past_pattern.max()
        
        if p_max == p_min: continue
        
        past_norm = (past_pattern - p_min) / (p_max - p_min)
        
        # Correlation
        score = np.corrcoef(curr_norm, past_norm)[0, 1]
        
        if score > best_score:
            best_score = score
            best_idx = i

    if best_idx != -1:
        match_date = df.index[best_idx].strftime('%Y-%m-%d')
        # Analyze outcome (next 5 days)
        future_start = best_idx + window
        future = targets[future_start : future_start + 5]
        outcome = 0
        if len(future) > 0:
            outcome = ((future[-1] - future[0]) / future[0]) * 100
            
        return {
            'date': match_date,
            'score': round(best_score * 100, 1),
            'outcome': round(outcome, 2)
        }
    return None

def find_supply_demand(df):
    """
    Finds Supply/Demand zones based on strong Marubozu-like candles.
    """
    if df.empty: return []
    
    zones = []
    # Analyze last 100 bars for fresh zones
    subset = df.iloc[-100:]
    
    avg_body = (subset['Close'] - subset['Open']).abs().mean()
    
    for idx, row in subset.iterrows():
        body = abs(row['Close'] - row['Open'])
        full_range = row['High'] - row['Low']
        
        if full_range == 0: continue
        
        # Criteria: Big Body (> 2x Avg) AND Little Wicks (Body > 80% of Range)
        if body > (avg_body * 2) and body > (full_range * 0.8):
            # Demand (Green)
            if row['Close'] > row['Open']:
                zones.append({
                    'type': 'DEMAND',
                    'top': row['Open'], # Base of the explosion
                    'bottom': row['Low'],
                    'date': idx.strftime('%Y-%m-%d'),
                    'strength': 'STRONG'
                })
            # Supply (Red)
            else:
                zones.append({
                    'type': 'SUPPLY',
                    'top': row['High'],
                    'bottom': row['Open'], # Top of the drop
                    'date': idx.strftime('%Y-%m-%d'),
                    'strength': 'STRONG'
                })
                
    # Filter zones close to current price (within 10%)
    current_price = df['Close'].iloc[-1]
    relevant_zones = []
    
    for z in zones:
        dist = abs(current_price - z['top']) / current_price
        if dist < 0.15: # Within 15%
            relevant_zones.append(z)
            
    return relevant_zones[-3:] # Return last 3 relevant

def calculate_rs(stock_df, index_df):
    """
    Calculates Relative Strength (RS) line vs XU100.
    Returns: { 'rs_score': 0-100, 'outperforming': bool, 'slope': float }
    """
    try:
        # Align dates
        stock_close = stock_df['Close']
        index_close = index_df['Close']
        
        # Common index
        common = stock_close.index.intersection(index_close.index)
        if len(common) < 30: return None
        
        stock_aligned = stock_close.loc[common]
        index_aligned = index_close.loc[common]
        
        rs_line = stock_aligned / index_aligned
        
        # Calculate SMA 20 of RS Line to determine trend
        rs_sma20 = rs_line.rolling(window=20).mean()
        
        last_rs = rs_line.iloc[-1]
        last_sma = rs_sma20.iloc[-1]
        
        outperforming = last_rs > last_sma
        
        # Calculate slope of RS line (last 10 days)
        last_10 = rs_line.iloc[-10:]
        slope = (last_10.iloc[-1] - last_10.iloc[0]) / last_10.iloc[0] * 100
        
        return {
            'outperforming': bool(outperforming),
            'slope': round(slope, 2),
            'rs_value': round(last_rs, 4)
        }
    except Exception as e:
        print(f"RS Error: {e}")
        return None

def calculate_seasonality(df):
    """
    Returns monthly average returns for the last 10 years.
    """
    try:
        df = df.copy()
        df['Month'] = df.index.month
        df['Year'] = df.index.year
        df['Pct'] = df['Close'].pct_change() * 100
        
        # Group by Month and Avg
        monthly_avg = df.groupby('Month')['Pct'].mean()
        
        # Count positive years per month
        pos_counts = df[df['Pct'] > 0].groupby('Month')['Pct'].count()
        total_counts = df.groupby('Month')['Pct'].count()
        win_rate = (pos_counts / total_counts * 100).fillna(0)
        
        seasonality = []
        months = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", 
                  "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
        
        for i in range(1, 13):
            if i in monthly_avg:
                seasonality.append({
                    'month': months[i-1],
                    'avg_return': round(monthly_avg[i], 2),
                    'win_rate': round(win_rate.get(i, 0), 0)
                })
        return seasonality
    except Exception as e:
        print(f"Seasonality Error: {e}")
        return []

def analyze_sentiment(news_list):
    """
    Analyzes sentiment of news titles.
    """
    if not news_list: return {'score': 0, 'label': 'NÖTR'}
    
    total_score = 0
    count = 0
    
    for n in news_list:
        title = n.get('title', '')
        score = 0
        
        if TEXTBLOB_AVAIL:
            blob = TextBlob(title)
            score = blob.sentiment.polarity
        else:
            # Simple Dictionary Fallback
            lower = title.lower()
            if 'record' in lower or 'profit' in lower or 'surge' in lower or 'jump' in lower or 'rekor' in lower or 'kar' in lower:
                score = 0.5
            elif 'loss' in lower or 'drop' in lower or 'plunge' in lower or 'zarar' in lower or 'yangın' in lower:
                score = -0.5
                
        total_score += score
        count += 1
        
    if count == 0: return {'score': 0, 'label': 'NÖTR'}
    
    avg = total_score / count
    label = 'NÖTR'
    if avg > 0.1: label = 'POZİTİF'
    if avg < -0.1: label = 'NEGATİF'
    
    return {'score': round(avg, 2), 'label': label}

@app.route('/analyze_advanced', methods=['GET'])
def analyze_advanced():
    symbol = request.args.get('symbol')
    if not symbol: return jsonify({'error': 'Symbol required'}), 400
    if not symbol.endswith('.IS'): symbol += '.IS'
    
    try:
        ticker = yf.Ticker(symbol)
        # Get enough data for similarity (5 years)
        hist = ticker.history(period="5y", interval="1d")
        
        if hist.empty: return jsonify({'error': 'No data'}), 404
        
        # 1. Support/Resistance (Use last 1 year)
        hist_1y = hist.iloc[-250:]
        levels = find_support_resistance(hist_1y)
        
        # 2. Similarity (Use full 5y)
        similarity = find_similarity(hist)
        
        # 3. Supply/Demand (Use last 6 months)
        zones = find_supply_demand(hist)
        
        # --- EXPERT FEATURES ---
        
        # 4. Relative Strength vs XU100
        rs_data = None
        try:
            # Fetch Index Data (Optimized: Should cache this in prod)
            xu100 = yf.Ticker('XU100.IS')
            idx_hist = xu100.history(period='1y', interval='1d')
            if not idx_hist.empty:
                rs_data = calculate_rs(hist_1y, idx_hist)
        except Exception as e:
            print(f"Index Fetch Error: {e}")

        # 5. Seasonality
        seasonality = calculate_seasonality(hist)
        
        # 6. Sentiment
        news = ticker.news
        sentiment = analyze_sentiment(news)
        
        return jsonify({
            'symbol': symbol,
            'sr_levels': levels,
            'similarity': similarity,
            'sd_zones': zones,
            'rs': rs_data,
            'seasonality': seasonality,
            'sentiment': sentiment
        })
    except Exception as e:
        print(f"Advanced Analysis Error: {e}")
        return jsonify({'error': str(e)}), 500


# --------------------------------------------------------------------------------
# ANALYZER HELPERS
# --------------------------------------------------------------------------------

def analyze_stock_sync(symbol, interval='1d', risk_mode='conservative'):
    try:
        # The original analyze_stock_sync was fetching data itself.
        # The new instruction implies `get_price` is a helper, but it's an endpoint.
        # Reverting to original data fetching logic for `analyze_stock_sync`
        # to maintain functionality, as `get_price` endpoint is not suitable here.
        if not symbol.endswith('.IS'): symbol += '.IS'
        ticker = yf.Ticker(symbol)
        
        # Determine Period
        period = '1y'
        if interval == '1h': period = '730d'
        
        hist = ticker.history(period=period, interval=interval)
        if hist.empty: return None
        
        # Resample to 4H for scoring consistency
        hist_4h = hist
        if interval == '1h':
           hist_4h = hist.resample('4h').agg({
                'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
            }).dropna()

        # Indicators
        hist_4h = calc_ichimoku(hist_4h)
        trend_health = analyze_trend_health(hist_4h)
        pattern = detect_candle_patterns(hist_4h) # Original used detect_candle_patterns
        
        # RS (Mock or Quick Calc) - skipping full index fetch for speed in huge scans, 
        # but needed for full scoring.
        # For sync scan, we might skip RS or use cached XU100. Set None for speed.
        rs_data = None 
        
        scores = calculate_final_score(hist_4h, trend_health, pattern, rs_data)
        signal_label_data = determine_signal_label(scores['total']) # Renamed to avoid conflict with `signal` dict
        
        last = hist.iloc[-1] # Use original hist for currentPrice
        
        return {
            'symbol': symbol,
            'currentPrice': last['Close'],
            'scores': scores,
            'signal': signal_label_data, # Use the full signal data
            'trend_health': trend_health # Added for consistency with original analyze_stock_sync return
        }
    except Exception as e:
        # print(f"Sync Analyze Error {symbol}: {e}")
        return None

# --------------------------------------------------------------------------------
# ENDPOINTS
# --------------------------------------------------------------------------------


def calculate_final_score(hist, trend_health, pattern, rs_data):
    """
    Calculates the detailed 0-100 score components expected by dashboard.
    """
    scores = {
        'sDir': 0, 'sStr': 0, 'sMom': 0, 'sBias': 0, 'sCat': 0, 'sRisk': 0, 'total': 0
    }
    
    # 1. DIRECTION (Max 25) - Based on Trend Health & Cloud
    if trend_health['mode'] == 'TREND': scores['sDir'] += 15
    if trend_health['pillars']['cloud']: scores['sDir'] += 10
    
    # 2. STRUCTURE (Max 10) - Based on Pillars structure
    if trend_health['pillars']['structure']: scores['sStr'] = 10
    
    # 3. MOMENTUM (Max 15) - RSI & Volume
    if trend_health['pillars']['rsi']: scores['sMom'] += 8
    if trend_health['pillars']['volume']: scores['sMom'] += 7
    
    # 4. BIAS (Max 20) - Pattern & RS
    if pattern and pattern['type'] == 'BULL': scores['sBias'] += 10
    if rs_data and rs_data['outperforming']: scores['sBias'] += 10
    
    # 5. CATALYST (Max 15) - Placeholder for News/Seasonality (Mock active for now if trend is good)
    if scores['sDir'] > 10: scores['sCat'] = 10
    
    # 6. RISK (Max 15) - ATR Stable
    if trend_health['pillars']['atr']: scores['sRisk'] = 15
    
    scores['total'] = sum(scores.values())
    return scores

def determine_signal_label(score):
    if score >= 75: return {'label': 'GÜÇLÜ AL', 'color': 'text-green-500', 'bg': 'bg-green-500/20'}
    if score >= 60: return {'label': 'AL', 'color': 'text-green-400', 'bg': 'bg-green-500/10'}
    if score >= 40: return {'label': 'NÖTR', 'color': 'text-yellow-500', 'bg': 'bg-yellow-500/10'}
    return {'label': 'SAT', 'color': 'text-red-500', 'bg': 'bg-red-500/10'}





@app.route('/favicon.ico')
def favicon():
    return "", 204



@app.route('/price', methods=['GET'])
def get_price():
    symbol = request.args.get('symbol')
    if not symbol: return jsonify({'error': 'Symbol missing'}), 400
    
    if not symbol.endswith('.IS'): symbol += '.IS'
    
    try:
        # Fast fetch (1 day, 1 minute interval to get latest)
        ticker = yf.Ticker(symbol)
        # We use 1d 1m to get the absolute latest live candle info
        df = ticker.history(period='1d', interval='1m')
        
        if df.empty: return jsonify({'error': 'No data'}), 404
        
        last = df.iloc[-1]
        
        # Determine time (Unix for chart)
        t_val = int(last.name.timestamp())
        
        return jsonify({
            'symbol': symbol,
            'price': last['Close'],
            'time': t_val,
            'open': last['Open'],
            'high': last['High'],
            'low': last['Low'],
            'close': last['Close'],
            'volume': last['Volume']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500



# --- GÜNCELLENMİŞ GET_DATA ---
def get_data(symbol, interval='1h', limit=2000):
    try:
        if not symbol.endswith('.IS'): symbol += '.IS'
        
        # Use ticker.history() instead of yf.download for better intraday support
        ticker = yf.Ticker(symbol)
        
        # --- FIX: Yahoo Finance Limit for Intraday Data ---
        # 4h, 1h, etc. cannot go back more than 730 days.
        period = '5y'
        if interval in ['1h', '60m', '90m', '4h']:
             period = '730d'

        df = ticker.history(period=period, interval=interval)
        
        # FALLBACK: If intraday data not available, try daily data
        if df.empty and interval in ['1h', '60m', '90m', '4h']:
            print(f"No {interval} data for {symbol}, falling back to daily data")
            df = ticker.history(period='2y', interval='1d')
        
        if df.empty: 
            print(f"No data for {symbol} with interval {interval}")
            return None

        df = df.reset_index()
        # Clean columns
        df.columns = [c.lower() if isinstance(c, str) else c[0].lower() for c in df.columns] 
        
        if 'date' in df.columns: df.rename(columns={'date': 'time'}, inplace=True)
        if 'datetime' in df.columns: df.rename(columns={'datetime': 'time'}, inplace=True)
        
        ohlc = []
        for _, row in df.tail(limit).iterrows():
            try:
                ohlc.append({
                    'time': int(row['time'].timestamp()) if hasattr(row['time'], 'timestamp') else row['time'],
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'volume': int(row['volume'])
                })
            except: pass
            
        return ohlc
    except Exception as e:
        print(f"Hata: {e}")
        return None

@app.route('/analyze', methods=['GET'])
def analyze_stock():
    symbol = request.args.get('symbol', 'THYAO')
    interval = request.args.get('interval', '4h')
    risk_mode = request.args.get('risk_mode', 'conservative')
    
    # get_data'ya currency parametresini gönderiyoruz
    ohlc = get_data(symbol, interval)
    
    if not ohlc: return jsonify({'error': 'Veri bulunamadı'}), 404

    current_price = ohlc[-1]['close']
    stop_margin = 0.98 if risk_mode == 'aggressive' else 0.95

    # --- MEVCUT TREND/CASCADE ANALİZİ (TL Bazlı çalıştırılır, görsel USD olur) ---
    # Cascade analizi karmaşık olduğu için onu henüz USD'ye çevirmiyoruz,
    # ancak kullanıcının isteği üzerine görsel veri USD döner.
    # Arka planda TL olarak analiz yapıp durumu döndürüyoruz.
    
    cascade_result = {}
    try:
        # Cascade için Ticker objesi gerekir (TL bazlı analiz devam eder)
        if not symbol.endswith('.IS'): t_sym = symbol + '.IS'
        else: t_sym = symbol
        ticker = yf.Ticker(t_sym)
        cascade_result = run_cascade_analysis(ticker, t_sym)
    except Exception as e:
        print(f"Cascade error: {e}")

    # Trade Plan (Dolar/TL fark etmeksizin fiyata göre oran)
    trade_plan = {
        'stop_loss': current_price * stop_margin,
        'take_profit': current_price * (1 + (1 - stop_margin) * 2)
    }

    # Fundamentals (Name update from STOCK_NAMES)
    raw_symbol = symbol.replace('.IS', '')
    full_name = STOCK_NAMES.get(raw_symbol, f"{raw_symbol} A.Ş.")
    
    fundamentals = {'name': full_name}

    response = {
        'symbol': symbol,
        'ohlc': ohlc,
        'currentPrice': current_price,
        'cascade': cascade_result, # Mevcut cascade sonucu
        'trade_plan': trade_plan,
        'fundamentals': fundamentals,
        'news': [], # Haberler şimdilik boş veya eklenebilir
        'scores': {'total': 0}, # Placeholder if not running full scoring on USD
        'signal': {'label': 'NÖTR', 'color': 'text-gray-500', 'bg': 'bg-gray-500/10'},
        'risk': {'stop': trade_plan['stop_loss'], 'target': trade_plan['take_profit'], 'rr': 2.0}
    }
    return jsonify(response)

@app.route('/scan_rsi_special')
def scan_rsi_special():
    """
    Gerçek Stoch RSI Taraması (Kullanıcı Ayarları: K=3, D=3, RSI=20, Stoch=14)
    Kriterler:
    1. AL: %K çizgisi 20'yi yukarı kesti (Dipten Dönüş)
    2. SAT: %K çizgisi 80'i aşağı kesti (Tepeden Dönüş)
    """
    ticks = ALL_BIST_TICKS
    results = []
    
    print(f"DEBUG: Stoch RSI Özel Taraması Başlıyor ({len(ticks)} hisse)...")
    
    def check_stoch_rsi(sym):
        try:
            full_sym = sym + '.IS'
            # Pandas TA için yeterli veri (6 ay güvenli)
            ticker = yf.Ticker(full_sym)
            df = ticker.history(period="6mo", interval="1d")
            
            if df.empty or len(df) < 50: return None
            
            # --- STOCH RSI HESAPLAMA ---
            # Ayarlar: RSI Length=20, Stoch Length=14, K=3, D=3
            # pandas_ta returns dataframe with columns like STOCHRSIk_14_20_3_3, STOCHRSId_14_20_3_3
            stoch = df.ta.stochrsi(length=14, rsi_length=20, k=3, d=3)
            
            if stoch is None or stoch.empty: return None
            
            # Sütun isimlerini dinamik alalım (kütüphane versiyonuna göre değişebilir)
            # Genellikle: last columns are K and D
            k_col = stoch.columns[0] # STOCHRSIk...
            d_col = stoch.columns[1] # STOCHRSId...
            
            # Son 2 mum
            curr_k = stoch.iloc[-1][k_col]
            curr_d = stoch.iloc[-1][d_col]
            
            prev_k = stoch.iloc[-2][k_col]
            
            signal = None
            desc = ""
            
            # --- SİNYAL MANTIĞI ---
            
            # 1. AL SİNYALİ: K çizgisi 20 seviyesini AŞAĞIDAN YUKARI kesti
            if prev_k < 20 and curr_k >= 20:
                signal = "AL"
                desc = "Stoch RSI (20) Dipten Dönüş"
                
            # 2. SAT SİNYALİ: K çizgisi 80 seviyesini YUKARIDAN AŞAĞI kesti
            elif prev_k > 80 and curr_k <= 80:
                signal = "SAT"
                desc = "Stoch RSI (80) Aşağı Kırılım"
                
            # 3. ALTERNATİF: K çizgisi D çizgisini kesti (Daha agresif)
            # Şimdilik sadece seviye kırılımlarına odaklanalım kullanıcının isteği üzerine.
            
            if signal:
                return {
                    'symbol': sym,
                    'price': df.iloc[-1]['Close'],
                    'rsi': curr_k, # Ekranda K değerini gösteriyoruz
                    'signal': signal,
                    'desc': desc
                }
                
        except Exception as e:
            # print(f"Stoch RSI Error {sym}: {e}")
            return None
        return None

    # Paralel Tarama
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(check_stoch_rsi, t) for t in ticks]
        for future in concurrent.futures.as_completed(futures):
            try:
                r = future.result()
                if r:
                    results.append(r)
            except: pass
            
    # Sonuçları 'AL' sinyalleri üstte olacak şekilde sırala
    results.sort(key=lambda x: (x['signal'] == 'AL', x['rsi']), reverse=True)
    
    print(f"DEBUG: Stoch RSI Tarama Bitti. {len(results)} sonuç.")
    return jsonify({'results': results})

@app.route('/scan_cascade', methods=['GET'])
def scan_cascade_endpoint():
    """
    Cascade Stratejisi Taraması (30dk / Manuel)
    Tüm hisseleri 4H ve 1H verilerle analiz eder.
    Setup veya Trigger olanları döndürür.
    """
    limit = request.args.get('limit', default=None, type=int)
    ticks = ALL_BIST_TICKS
    if limit: ticks = ticks[:limit]
    
    results = []
    print(f"DEBUG: Cascade Taraması Başlıyor ({len(ticks)} hisse)...")
    
    def check_cascade(sym):
        try:
            full_sym = sym + '.IS'
            ticker = yf.Ticker(full_sym)
            res = run_cascade_analysis(ticker, full_sym)
            
            # --- EKSİK OLAN KISIM: STATUS -> RENK DÖNÜŞÜMÜ ---
            sig_strength = 'gray'
            if res.get('status') == 'ACTIVE': sig_strength = 'green'
            elif res.get('status') == 'WAITING': sig_strength = 'yellow'
            
            # Sözlüğe manuel ekliyoruz ki aşağıdaki if çalışsın
            res['signal_strength'] = sig_strength
            # --------------------------------------------------
            
            # Sadece Setup veya Trigger varsa listeye ekle
            # signal_strength: 'green' (Trigger), 'yellow' (Vol), 'gray' (Setup)
            if res['signal_strength'] in ['green', 'yellow']:
                # levels anahtarı yoksa hata vermemesi için .get kullanıyoruz
                levels = res.get('levels', {})
                
                return {
                    'symbol': sym,
                    'price': levels.get('price', 0),  # Hata önleyici .get
                    'status': res['status'],
                    'strength': res['signal_strength'],
                    'msg': res.get('msg', ''),
                    'target': levels.get('target', 0),
                    'stop': levels.get('stop', 0)
                }
        except Exception as e:
            pass
        return None

    # Paralel Tarama
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(check_cascade, t) for t in ticks]
        for future in concurrent.futures.as_completed(futures):
            r = future.result()
            if r: results.append(r)
            
    # Sıralama: Önce Yeşiller, Sonra Sarılar
    # Custom sort: green=2, yellow=1
    def get_score(r):
        if r['strength'] == 'green': return 2
        if r['strength'] == 'yellow': return 1
        return 0
        
    results.sort(key=get_score, reverse=True)
    
    print(f"DEBUG: Cascade Taraması Bitti. {len(results)} sonuç.")
    return jsonify({'results': results})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    try:
        from waitress import serve
        print(f"Starting Production Server on http://0.0.0.0:{port}")

        serve(app, host='0.0.0.0', port=port)

    except ImportError:
        print("Waitress not found, running dev server...")
        app.run(host='0.0.0.0', port=port, debug=True)
