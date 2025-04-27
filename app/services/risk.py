from typing import List, Dict, Optional
from decimal import Decimal
from datetime import datetime, timedelta
from ..models.risk import (
    RiskLimit, TradingRestriction, UserPreference,
    CurrencyPair, Currency
)
from ..models.user import User
from .cache import cache_service
import json
import logging

logger = logging.getLogger(__name__)

class RiskManagementService:
    def __init__(self):
        self.cache_ttl = 300  # 5 minutes

    async def get_risk_limits(self, user: User, currency: str) -> RiskLimit:
        cache_key = f"risk_limits:{user.id}:{currency}"
        cached_limits = await cache_service.get(cache_key)
        
        if cached_limits:
            return json.loads(cached_limits)
        
        limits = await RiskLimit.get_or_none(user=user, currency=currency, is_active=True)
        if limits:
            await cache_service.set(cache_key, json.dumps(limits.to_dict()), expire=self.cache_ttl)
        return limits

    async def update_risk_limits(
        self,
        user: User,
        currency: str,
        daily_limit: Optional[Decimal] = None,
        weekly_limit: Optional[Decimal] = None,
        monthly_limit: Optional[Decimal] = None,
        max_trade_size: Optional[Decimal] = None,
        max_leverage: Optional[Decimal] = None,
        stop_loss_percentage: Optional[Decimal] = None,
        take_profit_percentage: Optional[Decimal] = None
    ) -> RiskLimit:
        limits = await RiskLimit.get_or_none(user=user, currency=currency)
        if not limits:
            limits = await RiskLimit.create(
                user=user,
                currency=currency,
                daily_limit=daily_limit or Decimal('0'),
                weekly_limit=weekly_limit or Decimal('0'),
                monthly_limit=monthly_limit or Decimal('0'),
                max_trade_size=max_trade_size or Decimal('0'),
                max_leverage=max_leverage or Decimal('1'),
                stop_loss_percentage=stop_loss_percentage or Decimal('0'),
                take_profit_percentage=take_profit_percentage or Decimal('0')
            )
        else:
            if daily_limit is not None:
                limits.daily_limit = daily_limit
            if weekly_limit is not None:
                limits.weekly_limit = weekly_limit
            if monthly_limit is not None:
                limits.monthly_limit = monthly_limit
            if max_trade_size is not None:
                limits.max_trade_size = max_trade_size
            if max_leverage is not None:
                limits.max_leverage = max_leverage
            if stop_loss_percentage is not None:
                limits.stop_loss_percentage = stop_loss_percentage
            if take_profit_percentage is not None:
                limits.take_profit_percentage = take_profit_percentage
            await limits.save()
        
        await cache_service.delete(f"risk_limits:{user.id}:{currency}")
        return limits

    async def check_trading_restrictions(
        self,
        user: User,
        currency_pair: str,
        amount: Decimal,
        order_type: str
    ) -> bool:
        restrictions = await TradingRestriction.filter(
            user=user,
            currency_pair=currency_pair,
            restriction_type=order_type,
            is_active=True
        ).first()
        
        if not restrictions:
            return True
        
        current_time = datetime.now().time()
        current_day = datetime.now().weekday()
        
        if restrictions.start_time and restrictions.end_time:
            if not (restrictions.start_time <= current_time <= restrictions.end_time):
                return False
        
        if current_day not in restrictions.days_of_week:
            return False
        
        if amount < restrictions.min_amount or amount > restrictions.max_amount:
            return False
        
        return True

    async def get_user_preferences(self, user: User) -> UserPreference:
        cache_key = f"user_preferences:{user.id}"
        cached_prefs = await cache_service.get(cache_key)
        
        if cached_prefs:
            return json.loads(cached_prefs)
        
        prefs = await UserPreference.get_or_none(user=user)
        if not prefs:
            prefs = await UserPreference.create(user=user)
        
        await cache_service.set(cache_key, json.dumps(prefs.to_dict()), expire=self.cache_ttl)
        return prefs

    async def update_user_preferences(
        self,
        user: User,
        theme: Optional[str] = None,
        language: Optional[str] = None,
        timezone: Optional[str] = None,
        notification_preferences: Optional[Dict] = None,
        trading_view_preferences: Optional[Dict] = None,
        chart_preferences: Optional[Dict] = None
    ) -> UserPreference:
        prefs = await self.get_user_preferences(user)
        
        if theme is not None:
            prefs.theme = theme
        if language is not None:
            prefs.language = language
        if timezone is not None:
            prefs.timezone = timezone
        if notification_preferences is not None:
            prefs.notification_preferences = notification_preferences
        if trading_view_preferences is not None:
            prefs.trading_view_preferences = trading_view_preferences
        if chart_preferences is not None:
            prefs.chart_preferences = chart_preferences
        
        await prefs.save()
        await cache_service.delete(f"user_preferences:{user.id}")
        return prefs

    async def get_currency_pairs(self) -> List[CurrencyPair]:
        cache_key = "currency_pairs:active"
        cached_pairs = await cache_service.get(cache_key)
        
        if cached_pairs:
            return [CurrencyPair.from_dict(pair) for pair in json.loads(cached_pairs)]
        
        pairs = await CurrencyPair.filter(is_active=True)
        await cache_service.set(cache_key, json.dumps([pair.to_dict() for pair in pairs]), expire=self.cache_ttl)
        return pairs

    async def get_currencies(self) -> List[Currency]:
        cache_key = "currencies:active"
        cached_currencies = await cache_service.get(cache_key)
        
        if cached_currencies:
            return [Currency.from_dict(currency) for currency in json.loads(cached_currencies)]
        
        currencies = await Currency.filter(is_active=True)
        await cache_service.set(cache_key, json.dumps([currency.to_dict() for currency in currencies]), expire=self.cache_ttl)
        return currencies

    async def check_trade_limits(
        self,
        user: User,
        currency_pair: str,
        amount: Decimal,
        price: Decimal,
        order_type: str
    ) -> bool:
        # Get risk limits for both currencies in the pair
        base_currency, quote_currency = currency_pair.split('/')
        
        base_limits = await self.get_risk_limits(user, base_currency)
        quote_limits = await self.get_risk_limits(user, quote_currency)
        
        if not base_limits or not quote_limits:
            return True
        
        # Check daily limits
        daily_volume = await self._get_daily_volume(user, currency_pair)
        if daily_volume + amount > base_limits.daily_limit:
            return False
        
        # Check weekly limits
        weekly_volume = await self._get_weekly_volume(user, currency_pair)
        if weekly_volume + amount > base_limits.weekly_limit:
            return False
        
        # Check monthly limits
        monthly_volume = await self._get_monthly_volume(user, currency_pair)
        if monthly_volume + amount > base_limits.monthly_limit:
            return False
        
        # Check max trade size
        if amount > base_limits.max_trade_size:
            return False
        
        return True

    async def _get_daily_volume(self, user: User, currency_pair: str) -> Decimal:
        # Implement actual volume calculation from trade history
        return Decimal('0')

    async def _get_weekly_volume(self, user: User, currency_pair: str) -> Decimal:
        # Implement actual volume calculation from trade history
        return Decimal('0')

    async def _get_monthly_volume(self, user: User, currency_pair: str) -> Decimal:
        # Implement actual volume calculation from trade history
        return Decimal('0')

risk_service = RiskManagementService() 