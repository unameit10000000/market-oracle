#!/usr/bin/env python3
"""
Test script to fetch latest chart data from Kraken API
Gets current price and OHLCV data for BTC/USDT
"""

import os
import json
import urllib.request
import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Kraken API configuration
API_BASE = "https://api.kraken.com"
API_KEY_PUBLIC = os.getenv("API_KEY")
API_KEY_PRIVATE = os.getenv("PRIVATE_KEY")

# For BTC/USDT, Kraken uses XBTUSDT (XBT is Bitcoin on Kraken)
TRADE_SYMBOL = "XBTUSDT"  # BTC/USDT pair on Kraken

def kraken_request(uri_path, data=None, private=False):
    """
    Make a request to Kraken API
    Similar to the tradingbot implementation
    """
    url = API_BASE + uri_path
    headers = {"User-Agent": "Market Oracle Test Script"}

    if private:
        import base64
        import hashlib
        import hmac
        
        api_nonce = str(int(time.time() * 1000))
        post_data = f"nonce={api_nonce}"
        if data:
            post_data += "&" + "&".join([f"{k}={v}" for k, v in data.items()])

        api_sha256 = hashlib.sha256(api_nonce.encode("utf8") + post_data.encode("utf8"))
        api_hmac = hmac.new(
            base64.b64decode(API_KEY_PRIVATE),
            uri_path.encode("utf8") + api_sha256.digest(),
            hashlib.sha512,
        )
        api_signature = base64.b64encode(api_hmac.digest())

        headers["API-Key"] = API_KEY_PUBLIC
        headers["API-Sign"] = api_signature

        req = urllib.request.Request(url, post_data.encode("utf8"), headers)
    else:
        req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req) as res:
            response = json.loads(res.read().decode())
            return response
    except Exception as e:
        print(f"❌ API Request failed: {e}")
        raise


def get_current_price(symbol):
    """
    Get current ticker price for a symbol
    Returns: current price (float) or None
    """
    try:
        print(f"📊 Fetching current price for {symbol}...")
        ticker_data = kraken_request(f"/0/public/Ticker?pair={symbol}")
        
        if ticker_data.get("error"):
            print(f"❌ Error: {ticker_data['error']}")
            return None
            
        # Extract current price (last trade price)
        pair_data = ticker_data['result'].get(symbol, {})
        if not pair_data:
            print(f"❌ No data found for pair: {symbol}")
            return None
            
        current_price = float(pair_data['c'][0])  # 'c' is the last trade price array [price, volume]
        volume_24h = float(pair_data['v'][1]) if 'v' in pair_data else None  # 24h volume
        
        print(f"✅ Current Price: ${current_price:,.2f}")
        if volume_24h:
            print(f"📈 24h Volume: ${volume_24h:,.2f}")
            
        return {
            "price": current_price,
            "volume_24h": volume_24h,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Failed to fetch ticker: {e}")
        return None


def get_ohlcv_data(symbol, interval=240, count=100):
    """
    Get OHLCV (candlestick) data for a symbol
    
    Args:
        symbol: Trading pair symbol (e.g., "XBTUSDT")
        interval: Candle interval in minutes (1, 5, 15, 30, 60, 240, 1440, 10080, 21600)
                 240 = 4 hours, 60 = 1 hour, 15 = 15 minutes
        count: Number of candles to return (max 720)
    
    Returns: List of candle data or None
    """
    try:
        interval_name = {
            1: "1 minute",
            5: "5 minutes",
            15: "15 minutes",
            30: "30 minutes",
            60: "1 hour",
            240: "4 hours",
            1440: "1 day",
            10080: "1 week",
            21600: "15 days"
        }.get(interval, f"{interval} minutes")
        
        print(f"📊 Fetching {interval_name} OHLCV data for {symbol}...")
        response = kraken_request(f"/0/public/OHLC?pair={symbol}&interval={interval}")
        
        if response.get("error"):
            print(f"❌ Error: {response['error']}")
            return None
            
        pair_data = response['result'].get(symbol, [])
        if not pair_data:
            print(f"❌ No data found for pair: {symbol}")
            return None
        
        # Convert to structured format
        candles = []
        for candle in pair_data[-count:]:  # Last N candles
            candles.append({
                "time": int(candle[0]),  # Unix timestamp
                "datetime": datetime.fromtimestamp(int(candle[0])).isoformat(),
                "open": float(candle[1]),
                "high": float(candle[2]),
                "low": float(candle[3]),
                "close": float(candle[4]),
                "vwap": float(candle[5]) if len(candle) > 5 else None,  # Volume weighted average price
                "volume": float(candle[6]) if len(candle) > 6 else None,
                "count": int(candle[7]) if len(candle) > 7 else None  # Number of trades
            })
        
        print(f"✅ Retrieved {len(candles)} candles")
        if candles:
            latest = candles[-1]
            print(f"📅 Latest candle: {latest['datetime']}")
            print(f"   Open: ${latest['open']:,.2f}")
            print(f"   High: ${latest['high']:,.2f}")
            print(f"   Low: ${latest['low']:,.2f}")
            print(f"   Close: ${latest['close']:,.2f}")
            if latest['volume']:
                print(f"   Volume: {latest['volume']:,.2f}")
        
        return candles
        
    except Exception as e:
        print(f"❌ Failed to fetch OHLCV data: {e}")
        return None


def main():
    """
    Main test function
    """
    print("=" * 60)
    print("🧪 Kraken API Test - BTC/USDT Chart Data")
    print("=" * 60)
    print()
    
    # Check if API keys are configured
    if not API_KEY_PUBLIC:
        print("⚠️  WARNING: API_KEY not set in .env file")
        print("   Public endpoints will still work, but private endpoints won't")
    else:
        print(f"✅ API Key configured: {API_KEY_PUBLIC[:20]}...")
    print()
    
    # Test 1: Get current price
    print("=" * 60)
    print("TEST 1: Current Price (Ticker)")
    print("=" * 60)
    price_data = get_current_price(TRADE_SYMBOL)
    print()
    
    # Test 2: Get OHLCV data (15 minute candles - last 50)
    print("=" * 60)
    print("TEST 2: OHLCV Data (15 minute candles, last 50)")
    print("=" * 60)
    ohlcv_15m = get_ohlcv_data(TRADE_SYMBOL, interval=15, count=50)
    print()
    
    # Test 3: Get OHLCV data (1 hour candles - last 24)
    print("=" * 60)
    print("TEST 3: OHLCV Data (1 hour candles, last 24)")
    print("=" * 60)
    ohlcv_1h = get_ohlcv_data(TRADE_SYMBOL, interval=60, count=24)
    print()
    
    # Test 4: Get OHLCV data (4 hour candles - last 30)
    print("=" * 60)
    print("TEST 4: OHLCV Data (4 hour candles, last 30)")
    print("=" * 60)
    ohlcv_4h = get_ohlcv_data(TRADE_SYMBOL, interval=240, count=30)
    print()
    
    # Summary
    print("=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    if price_data:
        print(f"✅ Current BTC/USDT Price: ${price_data['price']:,.2f}")
    if ohlcv_15m:
        print(f"✅ 15m candles: {len(ohlcv_15m)} candles retrieved")
    if ohlcv_1h:
        print(f"✅ 1h candles: {len(ohlcv_1h)} candles retrieved")
    if ohlcv_4h:
        print(f"✅ 4h candles: {len(ohlcv_4h)} candles retrieved")
    
    print()
    print("💡 Usage in code:")
    print("   - Current price: Use get_current_price('XBTUSDT')")
    print("   - OHLCV data: Use get_ohlcv_data('XBTUSDT', interval=60, count=100)")
    print("   - Available intervals: 1, 5, 15, 30, 60, 240, 1440, 10080, 21600 (minutes)")
    print()


if __name__ == "__main__":
    main()

