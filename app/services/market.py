from typing import List, Optional, Dict
from datetime import datetime, timedelta
from decimal import Decimal
import ccxt
import pandas as pd
import numpy as np
from ..models.market import MarketPrice, HistoricalPrice, MarketNews, MarketAnalysis
from .cache import cache_service
import json
import asyncio
from fastapi import WebSocket
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import talib
import aiohttp
import logging

logger = logging.getLogger(__name__)

class MarketService:
    def __init__(self):
        self.exchange = ccxt.binance()
        self.websocket_connections: List[WebSocket] = []
        self.price_update_interval = 60  # seconds
        self.news_update_interval = 300  # seconds

    async def add_websocket_connection(self, websocket: WebSocket):
        self.websocket_connections.append(websocket)

    async def remove_websocket_connection(self, websocket: WebSocket):
        if websocket in self.websocket_connections:
            self.websocket_connections.remove(websocket)

    async def broadcast_price_update(self, symbol: str, price_data: Dict):
        message = {
            "type": "price_update",
            "data": {
                "symbol": symbol,
                "price": str(price_data["price"]),
                "volume_24h": str(price_data["volume_24h"]),
                "change_24h": str(price_data["change_24h"]),
                "timestamp": datetime.now().isoformat()
            }
        }
        for connection in self.websocket_connections:
            try:
                await connection.send_json(message)
            except:
                await self.remove_websocket_connection(connection)

    async def get_current_price(self, symbol: str) -> Optional[MarketPrice]:
        cache_key = f"current_price:{symbol}"
        cached_price = await cache_service.get(cache_key)
        
        if cached_price:
            return MarketPrice(**json.loads(cached_price))

        try:
            ticker = self.exchange.fetch_ticker(symbol)
            price = await MarketPrice.create(
                symbol=symbol,
                price=Decimal(str(ticker["last"])),
                volume_24h=Decimal(str(ticker["quoteVolume"])),
                change_24h=Decimal(str(ticker["percentage"])),
                high_24h=Decimal(str(ticker["high"])),
                low_24h=Decimal(str(ticker["low"]))
            )
            
            await cache_service.set(cache_key, price.json(), expire=60)
            await self.broadcast_price_update(symbol, {
                "price": price.price,
                "volume_24h": price.volume_24h,
                "change_24h": price.change_24h
            })
            
            return price
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {str(e)}")
            return None

    async def get_historical_prices(
        self,
        symbol: str,
        interval: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[HistoricalPrice]:
        cache_key = f"historical_prices:{symbol}:{interval}:{start_time.isoformat()}:{end_time.isoformat()}"
        cached_data = await cache_service.get(cache_key)
        
        if cached_data:
            return [HistoricalPrice(**data) for data in json.loads(cached_data)]

        try:
            ohlcv = self.exchange.fetch_ohlcv(
                symbol,
                timeframe=interval,
                since=int(start_time.timestamp() * 1000),
                limit=1000
            )
            
            prices = []
            for data in ohlcv:
                prices.append(await HistoricalPrice.create(
                    symbol=symbol,
                    open_price=Decimal(str(data[1])),
                    high_price=Decimal(str(data[2])),
                    low_price=Decimal(str(data[3])),
                    close_price=Decimal(str(data[4])),
                    volume=Decimal(str(data[5])),
                    interval=interval,
                    timestamp=datetime.fromtimestamp(data[0] / 1000)
                ))
            
            await cache_service.set(cache_key, json.dumps([p.json() for p in prices]), expire=300)
            return prices
        except Exception as e:
            logger.error(f"Error fetching historical prices for {symbol}: {str(e)}")
            return []

    async def generate_technical_analysis(
        self,
        symbol: str,
        interval: str,
        timeframe: str
    ) -> Dict:
        end_time = datetime.now()
        start_time = end_time - timedelta(days=30)  # Default to 30 days
        
        prices = await self.get_historical_prices(symbol, interval, start_time, end_time)
        if not prices:
            return {}
        
        # Convert to pandas DataFrame
        df = pd.DataFrame([{
            'timestamp': p.timestamp,
            'open': float(p.open_price),
            'high': float(p.high_price),
            'low': float(p.low_price),
            'close': float(p.close_price),
            'volume': float(p.volume)
        } for p in prices])
        
        # Calculate technical indicators
        df['SMA_20'] = talib.SMA(df['close'], timeperiod=20)
        df['SMA_50'] = talib.SMA(df['close'], timeperiod=50)
        df['RSI'] = talib.RSI(df['close'], timeperiod=14)
        df['MACD'], df['MACD_Signal'], df['MACD_Hist'] = talib.MACD(df['close'])
        
        # Generate chart
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                           vertical_spacing=0.03, subplot_titles=(symbol, 'Volume'),
                           row_heights=[0.7, 0.3])
        
        # Candlestick chart
        fig.add_trace(go.Candlestick(x=df['timestamp'],
                                    open=df['open'],
                                    high=df['high'],
                                    low=df['low'],
                                    close=df['close'],
                                    name='OHLC'),
                     row=1, col=1)
        
        # Moving averages
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['SMA_20'],
                                name='SMA 20', line=dict(color='blue')),
                     row=1, col=1)
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['SMA_50'],
                                name='SMA 50', line=dict(color='red')),
                     row=1, col=1)
        
        # Volume
        fig.add_trace(go.Bar(x=df['timestamp'], y=df['volume'],
                            name='Volume'),
                     row=2, col=1)
        
        # Update layout
        fig.update_layout(
            title=f'{symbol} Technical Analysis',
            yaxis_title='Price',
            xaxis_rangeslider_visible=False
        )
        
        # Generate analysis
        current_price = float(prices[-1].close_price)
        sma_20 = float(df['SMA_20'].iloc[-1])
        sma_50 = float(df['SMA_50'].iloc[-1])
        rsi = float(df['RSI'].iloc[-1])
        
        analysis = {
            "trend": "bullish" if current_price > sma_20 > sma_50 else "bearish",
            "rsi": rsi,
            "rsi_signal": "overbought" if rsi > 70 else "oversold" if rsi < 30 else "neutral",
            "chart": fig.to_json()
        }
        
        # Save analysis
        await MarketAnalysis.create(
            symbol=symbol,
            analysis_type="technical",
            content=json.dumps(analysis),
            indicators={
                "sma_20": sma_20,
                "sma_50": sma_50,
                "rsi": rsi
            },
            timeframe=timeframe
        )
        
        return analysis

    async def get_market_news(
        self,
        symbols: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[MarketNews]:
        cache_key = f"market_news:{','.join(symbols) if symbols else 'all'}:{limit}"
        cached_news = await cache_service.get(cache_key)
        
        if cached_news:
            return [MarketNews(**data) for data in json.loads(cached_news)]

        try:
            # In a real implementation, you would fetch news from an API
            # This is a placeholder for demonstration
            news = await MarketNews.filter(
                symbols__overlap=symbols if symbols else None
            ).order_by("-published_at").limit(limit)
            
            await cache_service.set(cache_key, json.dumps([n.json() for n in news]), expire=300)
            return news
        except Exception as e:
            logger.error(f"Error fetching market news: {str(e)}")
            return []

    async def start_price_updates(self):
        while True:
            try:
                # Update prices for major pairs
                symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT"]
                for symbol in symbols:
                    await self.get_current_price(symbol)
                await asyncio.sleep(self.price_update_interval)
            except Exception as e:
                logger.error(f"Error in price update loop: {str(e)}")
                await asyncio.sleep(5)

    async def start_news_updates(self):
        while True:
            try:
                # Update news
                await self.get_market_news()
                await asyncio.sleep(self.news_update_interval)
            except Exception as e:
                logger.error(f"Error in news update loop: {str(e)}")
                await asyncio.sleep(5)

market_service = MarketService() 