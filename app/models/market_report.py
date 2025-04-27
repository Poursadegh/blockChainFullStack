from tortoise import fields
from tortoise.models import Model
from datetime import datetime
from decimal import Decimal

class MarketData(Model):
    id = fields.BigIntField(pk=True)
    symbol = fields.CharField(max_length=20)
    price = fields.DecimalField(max_digits=20, decimal_places=8)
    volume_24h = fields.DecimalField(max_digits=20, decimal_places=8)
    market_cap = fields.DecimalField(max_digits=20, decimal_places=8)
    price_change_24h = fields.DecimalField(max_digits=10, decimal_places=2)  # percentage
    price_change_7d = fields.DecimalField(max_digits=10, decimal_places=2)  # percentage
    last_updated = fields.DatetimeField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "market_data"
        indexes = [("symbol", "last_updated")]

class MarketReport(Model):
    id = fields.BigIntField(pk=True)
    report_type = fields.CharField(max_length=50)  # daily, weekly, monthly
    start_date = fields.DatetimeField()
    end_date = fields.DatetimeField()
    top_gainers = fields.JSONField()  # List of top performing cryptocurrencies
    top_losers = fields.JSONField()  # List of worst performing cryptocurrencies
    market_summary = fields.JSONField()  # Overall market statistics
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "market_reports"
        indexes = [("report_type", "start_date")]

class UserMarketAlert(Model):
    id = fields.BigIntField(pk=True)
    user = fields.ForeignKeyField('models.User', related_name='market_alerts')
    symbol = fields.CharField(max_length=20)
    alert_type = fields.CharField(max_length=20)  # price_increase, price_decrease, volume_increase
    threshold = fields.DecimalField(max_digits=10, decimal_places=2)  # percentage
    is_active = fields.BooleanField(default=True)
    last_triggered = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "user_market_alerts"
        indexes = [("user_id", "symbol")] 