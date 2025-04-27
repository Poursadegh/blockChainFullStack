from fastapi import APIRouter, Depends, HTTPException
from typing import List
import ccxt
import pandas as pd
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/price")
async def get_btc_price():
    try:
        exchange = ccxt.binance()
        ticker = exchange.fetch_ticker('BTC/USDT')
        return {
            "symbol": "BTC/USDT",
            "price": ticker['last'],
            "high": ticker['high'],
            "low": ticker['low'],
            "volume": ticker['baseVolume'],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/historical")
async def get_historical_data(days: int = 7):
    try:
        exchange = ccxt.binance()
        since = exchange.parse8601((datetime.now() - timedelta(days=days)).isoformat())
        ohlcv = exchange.fetch_ohlcv('BTC/USDT', timeframe='1d', since=since)
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        return df.to_dict(orient='records')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/market-info")
async def get_market_info():
    try:
        exchange = ccxt.binance()
        markets = exchange.load_markets()
        btc_market = markets['BTC/USDT']
        
        return {
            "symbol": "BTC/USDT",
            "precision": btc_market['precision'],
            "limits": btc_market['limits'],
            "active": btc_market['active'],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 