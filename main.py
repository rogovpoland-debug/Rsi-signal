from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import pandas as pd
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")

def calculate_rsi(prices, window=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1] if not rsi.empty else 50.0

@app.get("/signal")
def get_rsi_signal(pair: str = "EUR/USD", interval: str = "5min"):
    if not TWELVE_DATA_API_KEY:
        return {"error": "TWELVE_DATA_API_KEY is not set"}
    
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": pair,
        "interval": interval,
        "outputsize": 20,
        "apikey": TWELVE_DATA_API_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        # ✅ ИСПРАВЛЕНО: Проверяем наличие "values"
        if "values" not in data:
            return {"error": "No 'values' in response", "response": data}
        
        closes = [float(bar["close"]) for bar in data["values"]]
        prices = pd.Series(closes)
        rsi = calculate_rsi(prices)
        
        signal = "NEUTRAL"
        if rsi < 30:
            signal = "BUY"
        elif rsi > 70:
            signal = "SELL"
        
        return {
            "pair": pair,
            "interval": interval,
            "price": closes[0],
            "rsi": round(float(rsi), 2),
            "signal": signal,
            "timestamp": data["values"][0]["datetime"]
        }
    except Exception as e:
        return {"error": str(e)}
