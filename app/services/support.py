from typing import List, Dict, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from ..models.support import (
    SupportTicket, TicketMessage, FAQCategory, FAQItem,
    UserAnalytics, FinancialReport, TicketStatus, TicketPriority
)
from ..models.user import User
from .cache import cache_service
import json
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

class SupportService:
    def __init__(self):
        self.cache_ttl = 300  # 5 minutes

    async def create_ticket(
        self,
        user: User,
        title: str,
        description: str,
        category: str,
        priority: str = "medium"
    ) -> SupportTicket:
        ticket = await SupportTicket.create(
            user=user,
            title=title,
            description=description,
            category=category,
            priority=priority
        )
        return ticket

    async def add_ticket_message(
        self,
        ticket: SupportTicket,
        user: User,
        message: str
    ) -> TicketMessage:
        ticket_message = await TicketMessage.create(
            ticket=ticket,
            user=user,
            message=message
        )
        
        # Update ticket status if it's a support agent responding
        if user.is_staff and ticket.status == TicketStatus.OPEN:
            ticket.status = TicketStatus.IN_PROGRESS
            await ticket.save()
        
        return ticket_message

    async def update_ticket_status(
        self,
        ticket: SupportTicket,
        status: TicketStatus,
        assigned_to: Optional[User] = None
    ) -> SupportTicket:
        ticket.status = status
        if assigned_to:
            ticket.assigned_to = assigned_to
        if status == TicketStatus.RESOLVED:
            ticket.resolved_at = datetime.now()
        await ticket.save()
        return ticket

    async def get_user_tickets(
        self,
        user: User,
        status: Optional[TicketStatus] = None
    ) -> List[SupportTicket]:
        query = SupportTicket.filter(user=user)
        if status:
            query = query.filter(status=status)
        return await query.order_by("-created_at")

    async def get_ticket_messages(
        self,
        ticket: SupportTicket,
        limit: int = 50
    ) -> List[TicketMessage]:
        return await TicketMessage.filter(
            ticket=ticket
        ).order_by("created_at").limit(limit)

    async def get_faq_categories(self) -> List[FAQCategory]:
        cache_key = "faq_categories"
        cached_categories = await cache_service.get(cache_key)
        
        if cached_categories:
            return [FAQCategory.from_dict(cat) for cat in json.loads(cached_categories)]
        
        categories = await FAQCategory.filter(
            is_active=True
        ).order_by("order")
        
        await cache_service.set(cache_key, json.dumps([cat.to_dict() for cat in categories]), expire=self.cache_ttl)
        return categories

    async def get_faq_items(self, category_id: Optional[int] = None) -> List[FAQItem]:
        cache_key = f"faq_items:{category_id if category_id else 'all'}"
        cached_items = await cache_service.get(cache_key)
        
        if cached_items:
            return [FAQItem.from_dict(item) for item in json.loads(cached_items)]
        
        query = FAQItem.filter(is_active=True)
        if category_id:
            query = query.filter(category_id=category_id)
        
        items = await query.order_by("order")
        await cache_service.set(cache_key, json.dumps([item.to_dict() for item in items]), expire=self.cache_ttl)
        return items

    async def update_user_analytics(self, user: User, date: datetime):
        analytics = await UserAnalytics.get_or_none(user=user, date=date.date())
        if not analytics:
            analytics = await UserAnalytics.create(user=user, date=date.date())
        
        analytics.login_count += 1
        await analytics.save()

    async def generate_financial_report(
        self,
        report_type: str,
        start_date: datetime,
        end_date: datetime
    ) -> FinancialReport:
        # Calculate financial metrics
        total_revenue = Decimal('0')
        total_expenses = Decimal('0')
        trading_fees = Decimal('0')
        withdrawal_fees = Decimal('0')
        other_income = Decimal('0')
        other_expenses = Decimal('0')

        # Here you would implement the actual financial calculations
        # based on your business logic and data sources

        net_profit = total_revenue - total_expenses

        report = await FinancialReport.create(
            report_type=report_type,
            start_date=start_date.date(),
            end_date=end_date.date(),
            total_revenue=total_revenue,
            total_expenses=total_expenses,
            net_profit=net_profit,
            trading_fees=trading_fees,
            withdrawal_fees=withdrawal_fees,
            other_income=other_income,
            other_expenses=other_expenses
        )

        return report

    async def get_user_analytics(
        self,
        user: User,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        analytics = await UserAnalytics.filter(
            user=user,
            date__gte=start_date.date(),
            date__lte=end_date.date()
        ).order_by("date")

        # Calculate summary statistics
        total_logins = sum(a.login_count for a in analytics)
        total_trading_volume = sum(a.trading_volume for a in analytics)
        total_trades = sum(a.trade_count for a in analytics)
        total_deposits = sum(a.deposit_amount for a in analytics)
        total_withdrawals = sum(a.withdrawal_amount for a in analytics)
        total_tickets = sum(a.support_tickets for a in analytics)

        return {
            "total_logins": total_logins,
            "total_trading_volume": total_trading_volume,
            "total_trades": total_trades,
            "total_deposits": total_deposits,
            "total_withdrawals": total_withdrawals,
            "total_tickets": total_tickets,
            "daily_data": [a.to_dict() for a in analytics]
        }

    async def get_support_metrics(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        tickets = await SupportTicket.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        )

        # Calculate support metrics
        total_tickets = len(tickets)
        resolved_tickets = len([t for t in tickets if t.status == TicketStatus.RESOLVED])
        avg_resolution_time = None
        category_distribution = defaultdict(int)
        priority_distribution = defaultdict(int)

        for ticket in tickets:
            category_distribution[ticket.category] += 1
            priority_distribution[ticket.priority] += 1

        if resolved_tickets > 0:
            resolution_times = [
                (t.resolved_at - t.created_at).total_seconds()
                for t in tickets
                if t.status == TicketStatus.RESOLVED and t.resolved_at
            ]
            avg_resolution_time = sum(resolution_times) / len(resolution_times)

        return {
            "total_tickets": total_tickets,
            "resolved_tickets": resolved_tickets,
            "resolution_rate": (resolved_tickets / total_tickets * 100) if total_tickets > 0 else 0,
            "average_resolution_time": avg_resolution_time,
            "category_distribution": dict(category_distribution),
            "priority_distribution": dict(priority_distribution)
        }

support_service = SupportService() 