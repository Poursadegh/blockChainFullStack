from tortoise import fields
from tortoise.models import Model
from datetime import datetime
from enum import Enum

class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"

class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class TicketCategory(str, Enum):
    TECHNICAL = "technical"
    ACCOUNT = "account"
    PAYMENT = "payment"
    TRADING = "trading"
    OTHER = "other"

class SupportTicket(Model):
    id = fields.BigIntField(pk=True)
    user = fields.ForeignKeyField('models.User', related_name='support_tickets')
    title = fields.CharField(max_length=200)
    description = fields.TextField()
    category = fields.CharEnumField(TicketCategory)
    priority = fields.CharEnumField(TicketPriority, default=TicketPriority.MEDIUM)
    status = fields.CharEnumField(TicketStatus, default=TicketStatus.OPEN)
    assigned_to = fields.ForeignKeyField('models.User', related_name='assigned_tickets', null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    resolved_at = fields.DatetimeField(null=True)

    class Meta:
        table = "support_tickets"
        indexes = [("user_id", "status"), ("category", "status")]

class TicketMessage(Model):
    id = fields.BigIntField(pk=True)
    ticket = fields.ForeignKeyField('models.SupportTicket', related_name='messages')
    user = fields.ForeignKeyField('models.User', related_name='ticket_messages')
    message = fields.TextField()
    is_read = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "ticket_messages"
        indexes = [("ticket_id", "created_at")]

class FAQCategory(Model):
    id = fields.BigIntField(pk=True)
    name = fields.CharField(max_length=100)
    description = fields.TextField(null=True)
    order = fields.IntField(default=0)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "faq_categories"
        indexes = [("order",)]

class FAQItem(Model):
    id = fields.BigIntField(pk=True)
    category = fields.ForeignKeyField('models.FAQCategory', related_name='items')
    question = fields.CharField(max_length=200)
    answer = fields.TextField()
    order = fields.IntField(default=0)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "faq_items"
        indexes = [("category_id", "order")]

class UserAnalytics(Model):
    id = fields.BigIntField(pk=True)
    user = fields.ForeignKeyField('models.User', related_name='analytics')
    date = fields.DateField()
    login_count = fields.IntField(default=0)
    trading_volume = fields.DecimalField(max_digits=20, decimal_places=8, default=0)
    trade_count = fields.IntField(default=0)
    deposit_amount = fields.DecimalField(max_digits=20, decimal_places=8, default=0)
    withdrawal_amount = fields.DecimalField(max_digits=20, decimal_places=8, default=0)
    support_tickets = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "user_analytics"
        indexes = [("user_id", "date")]

class FinancialReport(Model):
    id = fields.BigIntField(pk=True)
    report_type = fields.CharField(max_length=20)  # daily, weekly, monthly
    start_date = fields.DateField()
    end_date = fields.DateField()
    total_revenue = fields.DecimalField(max_digits=20, decimal_places=8)
    total_expenses = fields.DecimalField(max_digits=20, decimal_places=8)
    net_profit = fields.DecimalField(max_digits=20, decimal_places=8)
    trading_fees = fields.DecimalField(max_digits=20, decimal_places=8)
    withdrawal_fees = fields.DecimalField(max_digits=20, decimal_places=8)
    other_income = fields.DecimalField(max_digits=20, decimal_places=8)
    other_expenses = fields.DecimalField(max_digits=20, decimal_places=8)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "financial_reports"
        indexes = [("report_type", "start_date")] 