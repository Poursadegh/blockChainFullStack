from tortoise import fields
from tortoise.models import Model
from decimal import Decimal
from typing import Dict, List, Optional
from datetime import datetime

class RiskLimit(Model):
    id = fields.BigIntField(pk=True)
    user = fields.ForeignKeyField('models.User', related_name='risk_limits')
    currency = fields.CharField(max_length=10)
    daily_limit = fields.DecimalField(max_digits=20, decimal_places=8)
    weekly_limit = fields.DecimalField(max_digits=20, decimal_places=8)
    monthly_limit = fields.DecimalField(max_digits=20, decimal_places=8)
    max_trade_size = fields.DecimalField(max_digits=20, decimal_places=8)
    max_leverage = fields.DecimalField(max_digits=5, decimal_places=2)
    stop_loss_percentage = fields.DecimalField(max_digits=5, decimal_places=2)
    take_profit_percentage = fields.DecimalField(max_digits=5, decimal_places=2)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "risk_limits"
        indexes = [("user_id", "currency")]

class TradingRestriction(Model):
    id = fields.BigIntField(pk=True)
    user = fields.ForeignKeyField('models.User', related_name='trading_restrictions')
    restriction_type = fields.CharField(max_length=50)  # market, limit, stop, etc.
    currency_pair = fields.CharField(max_length=20)
    min_amount = fields.DecimalField(max_digits=20, decimal_places=8)
    max_amount = fields.DecimalField(max_digits=20, decimal_places=8)
    start_time = fields.TimeField(null=True)
    end_time = fields.TimeField(null=True)
    days_of_week = fields.JSONField()  # List of days (0-6)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "trading_restrictions"
        indexes = [("user_id", "currency_pair")]

class UserPreference(Model):
    id = fields.BigIntField(pk=True)
    user = fields.ForeignKeyField('models.User', related_name='preferences')
    theme = fields.CharField(max_length=20, default='light')  # light, dark, system
    language = fields.CharField(max_length=10, default='en')
    timezone = fields.CharField(max_length=50, default='UTC')
    notification_preferences = fields.JSONField(default=dict)
    trading_view_preferences = fields.JSONField(default=dict)
    chart_preferences = fields.JSONField(default=dict)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "user_preferences"

class CurrencyPair(Model):
    id = fields.BigIntField(pk=True)
    base_currency = fields.CharField(max_length=10)
    quote_currency = fields.CharField(max_length=10)
    symbol = fields.CharField(max_length=20, unique=True)
    is_active = fields.BooleanField(default=True)
    min_trade_amount = fields.DecimalField(max_digits=20, decimal_places=8)
    max_trade_amount = fields.DecimalField(max_digits=20, decimal_places=8)
    price_precision = fields.IntField()
    amount_precision = fields.IntField()
    min_price = fields.DecimalField(max_digits=20, decimal_places=8)
    max_price = fields.DecimalField(max_digits=20, decimal_places=8)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "currency_pairs"
        indexes = [("base_currency", "quote_currency")]

class Currency(Model):
    id = fields.BigIntField(pk=True)
    code = fields.CharField(max_length=10, unique=True)
    name = fields.CharField(max_length=100)
    symbol = fields.CharField(max_length=10)
    type = fields.CharField(max_length=20)  # fiat, crypto, stablecoin
    is_active = fields.BooleanField(default=True)
    decimals = fields.IntField(default=8)
    min_withdrawal = fields.DecimalField(max_digits=20, decimal_places=8)
    withdrawal_fee = fields.DecimalField(max_digits=20, decimal_places=8)
    deposit_fee = fields.DecimalField(max_digits=20, decimal_places=8)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "currencies" 