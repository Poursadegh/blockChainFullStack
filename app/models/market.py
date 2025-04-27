from tortoise import fields
from tortoise.models import Model
from datetime import datetime
from decimal import Decimal
from typing import Optional

class MarketPrice(Model):
    id = fields.BigIntField(pk=True)
    symbol = fields.CharField(max_length=20)  # e.g., BTC/USDT
    price = fields.DecimalField(max_digits=30, decimal_places=8)
    volume_24h = fields.DecimalField(max_digits=30, decimal_places=8)
    change_24h = fields.DecimalField(max_digits=10, decimal_places=4)
    high_24h = fields.DecimalField(max_digits=30, decimal_places=8)
    low_24h = fields.DecimalField(max_digits=30, decimal_places=8)
    timestamp = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "market_prices"
        indexes = [("symbol", "timestamp")]

class HistoricalPrice(Model):
    id = fields.BigIntField(pk=True)
    symbol = fields.CharField(max_length=20)
    open_price = fields.DecimalField(max_digits=30, decimal_places=8)
    high_price = fields.DecimalField(max_digits=30, decimal_places=8)
    low_price = fields.DecimalField(max_digits=30, decimal_places=8)
    close_price = fields.DecimalField(max_digits=30, decimal_places=8)
    volume = fields.DecimalField(max_digits=30, decimal_places=8)
    interval = fields.CharField(max_length=10)  # 1m, 5m, 15m, 1h, 4h, 1d
    timestamp = fields.DatetimeField()

    class Meta:
        table = "historical_prices"
        indexes = [("symbol", "interval", "timestamp")]

class MarketNews(Model):
    id = fields.BigIntField(pk=True)
    title = fields.CharField(max_length=255)
    content = fields.TextField()
    source = fields.CharField(max_length=100)
    url = fields.CharField(max_length=255)
    sentiment = fields.CharField(max_length=20, null=True)  # positive, negative, neutral
    impact = fields.CharField(max_length=20, null=True)  # high, medium, low
    symbols = fields.JSONField()  # List of related cryptocurrency symbols
    published_at = fields.DatetimeField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "market_news"
        indexes = [("symbols", "published_at")]

class MarketAnalysis(Model):
    id = fields.BigIntField(pk=True)
    symbol = fields.CharField(max_length=20)
    analysis_type = fields.CharField(max_length=50)  # technical, fundamental, sentiment
    content = fields.TextField()
    indicators = fields.JSONField()  # Technical indicators data
    timeframe = fields.CharField(max_length=10)  # 1h, 4h, 1d, 1w
    confidence = fields.DecimalField(max_digits=5, decimal_places=2)  # 0-100
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "market_analysis"
        indexes = [("symbol", "analysis_type", "timeframe")] 