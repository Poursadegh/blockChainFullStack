import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from ..core.config import settings

class TradingBot:
    def __init__(self):
        self.exchange = ccxt.binance({
            'apiKey': settings.BINANCE_API_KEY,
            'secret': settings.BINANCE_API_SECRET,
            'enableRateLimit': True
        })
        self.positions: Dict[str, float] = {}
        self.strategies = {
            'simple_moving_average': self.simple_moving_average_strategy,
            'rsi': self.rsi_strategy,
            'macd': self.macd_strategy
        }

    async def get_historical_data(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> pd.DataFrame:
        """Fetch historical price data"""
        ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df

    def calculate_rsi(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def calculate_macd(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calculate MACD indicator"""
        exp1 = data['close'].ewm(span=12, adjust=False).mean()
        exp2 = data['close'].ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        return {'macd': macd, 'signal': signal}

    async def simple_moving_average_strategy(self, symbol: str) -> str:
        """Simple Moving Average crossover strategy"""
        data = await self.get_historical_data(symbol)
        data['SMA20'] = data['close'].rolling(window=20).mean()
        data['SMA50'] = data['close'].rolling(window=50).mean()
        
        if data['SMA20'].iloc[-1] > data['SMA50'].iloc[-1] and data['SMA20'].iloc[-2] <= data['SMA50'].iloc[-2]:
            return 'buy'
        elif data['SMA20'].iloc[-1] < data['SMA50'].iloc[-1] and data['SMA20'].iloc[-2] >= data['SMA50'].iloc[-2]:
            return 'sell'
        return 'hold'

    async def rsi_strategy(self, symbol: str) -> str:
        """RSI strategy"""
        data = await self.get_historical_data(symbol)
        rsi = self.calculate_rsi(data)
        
        if rsi.iloc[-1] < 30:
            return 'buy'
        elif rsi.iloc[-1] > 70:
            return 'sell'
        return 'hold'

    async def macd_strategy(self, symbol: str) -> str:
        """MACD strategy"""
        data = await self.get_historical_data(symbol)
        macd_data = self.calculate_macd(data)
        
        if macd_data['macd'].iloc[-1] > macd_data['signal'].iloc[-1] and macd_data['macd'].iloc[-2] <= macd_data['signal'].iloc[-2]:
            return 'buy'
        elif macd_data['macd'].iloc[-1] < macd_data['signal'].iloc[-1] and macd_data['macd'].iloc[-2] >= macd_data['signal'].iloc[-2]:
            return 'sell'
        return 'hold'

    async def execute_trade(self, symbol: str, strategy: str, amount: float) -> Dict:
        """Execute a trade based on strategy"""
        if strategy not in self.strategies:
            raise ValueError(f"Unknown strategy: {strategy}")
        
        action = await self.strategies[strategy](symbol)
        
        if action == 'buy':
            order = self.exchange.create_market_buy_order(symbol, amount)
        elif action == 'sell':
            order = self.exchange.create_market_sell_order(symbol, amount)
        else:
            return {'action': 'hold', 'symbol': symbol}
        
        return {
            'action': action,
            'symbol': symbol,
            'amount': amount,
            'order_id': order['id'],
            'timestamp': datetime.now().isoformat()
        }

    async def get_portfolio_value(self) -> Dict[str, float]:
        """Get current portfolio value"""
        balance = self.exchange.fetch_balance()
        portfolio = {}
        
        for currency, amount in balance['total'].items():
            if amount > 0:
                if currency == 'USDT':
                    portfolio[currency] = amount
                else:
                    ticker = self.exchange.fetch_ticker(f"{currency}/USDT")
                    portfolio[currency] = amount * ticker['last']
        
        return portfolio 