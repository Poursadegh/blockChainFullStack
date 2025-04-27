from tortoise import fields
from tortoise.models import Model
from enum import Enum
from datetime import datetime

class OrderType(str, Enum):
    BUY = "buy"
    SELL = "sell"

class OrderStatus(str, Enum):
    PENDING = "pending"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"

class Order(Model):
    id = fields.BigIntField(pk=True)
    user = fields.ForeignKeyField('models.User', related_name='orders')
    symbol = fields.CharField(max_length=20)  # e.g., "BTC/USDT"
    order_type = fields.CharEnumField(OrderType)
    price = fields.DecimalField(max_digits=20, decimal_places=8)
    amount = fields.DecimalField(max_digits=20, decimal_places=8)
    filled_amount = fields.DecimalField(max_digits=20, decimal_places=8, default=0)
    status = fields.CharEnumField(OrderStatus, default=OrderStatus.PENDING)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "orders"
        indexes = [
            ("symbol", "order_type", "status"),
            ("user_id", "status"),
            ("created_at",)
        ]

class Trade(Model):
    id = fields.BigIntField(pk=True)
    symbol = fields.CharField(max_length=20)
    buyer = fields.ForeignKeyField('models.User', related_name='buy_trades')
    seller = fields.ForeignKeyField('models.User', related_name='sell_trades')
    price = fields.DecimalField(max_digits=20, decimal_places=8)
    amount = fields.DecimalField(max_digits=20, decimal_places=8)
    buy_order = fields.ForeignKeyField('models.Order', related_name='buy_trades')
    sell_order = fields.ForeignKeyField('models.Order', related_name='sell_trades')
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "trades"
        indexes = [
            ("symbol", "created_at"),
            ("buyer_id", "created_at"),
            ("seller_id", "created_at")
        ]

class OrderBook(Model):
    id = fields.BigIntField(pk=True)
    symbol = fields.CharField(max_length=20, unique=True)
    last_price = fields.DecimalField(max_digits=20, decimal_places=8, null=True)
    volume_24h = fields.DecimalField(max_digits=20, decimal_places=8, default=0)
    high_24h = fields.DecimalField(max_digits=20, decimal_places=8, null=True)
    low_24h = fields.DecimalField(max_digits=20, decimal_places=8, null=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "order_books"
        indexes = [("symbol",)] 