from typing import List, Dict, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from ..models.market_report import MarketData, MarketReport, UserMarketAlert
from ..models.user import User
from .cache import cache_service
import json
import logging
import aiohttp
import asyncio

logger = logging.getLogger(__name__)

class MarketReportService:
    def __init__(self):
        self.cache_ttl = 300  # 5 minutes
        self.api_url = "https://api.coingecko.com/api/v3"
        self.top_limit = 10  # Number of top gainers/losers to track

    async def fetch_market_data(self) -> List[MarketData]:
        """Fetch latest market data from external API"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/coins/markets", params={
                    "vs_currency": "usd",
                    "order": "market_cap_desc",
                    "per_page": 100,
                    "page": 1,
                    "sparkline": False,
                    "price_change_percentage": "24h,7d"
                }) as response:
                    data = await response.json()
                    
                    market_data = []
                    for coin in data:
                        market_data.append(await MarketData.create(
                            symbol=coin['symbol'].upper(),
                            price=Decimal(str(coin['current_price'])),
                            volume_24h=Decimal(str(coin['total_volume'])),
                            market_cap=Decimal(str(coin['market_cap'])),
                            price_change_24h=Decimal(str(coin['price_change_percentage_24h'])),
                            price_change_7d=Decimal(str(coin['price_change_percentage_7d_in_currency'])),
                            last_updated=datetime.fromisoformat(coin['last_updated'].replace('Z', '+00:00'))
                        ))
                    
                    return market_data
        except Exception as e:
            logger.error(f"Error fetching market data: {str(e)}")
            return []

    async def generate_market_report(self, report_type: str = "daily") -> MarketReport:
        """Generate market report with top gainers and losers"""
        cache_key = f"market_report:{report_type}:{datetime.now().date()}"
        cached_report = await cache_service.get(cache_key)
        
        if cached_report:
            return MarketReport.from_dict(json.loads(cached_report))

        # Calculate date range based on report type
        end_date = datetime.now()
        if report_type == "daily":
            start_date = end_date - timedelta(days=1)
        elif report_type == "weekly":
            start_date = end_date - timedelta(weeks=1)
        else:  # monthly
            start_date = end_date - timedelta(days=30)

        # Get market data for the period
        market_data = await MarketData.filter(
            last_updated__gte=start_date,
            last_updated__lte=end_date
        ).order_by("-last_updated")

        # Group data by symbol and calculate averages
        symbol_data = {}
        for data in market_data:
            if data.symbol not in symbol_data:
                symbol_data[data.symbol] = {
                    'price_changes': [],
                    'volumes': [],
                    'market_caps': []
                }
            symbol_data[data.symbol]['price_changes'].append(data.price_change_24h)
            symbol_data[data.symbol]['volumes'].append(data.volume_24h)
            symbol_data[data.symbol]['market_caps'].append(data.market_cap)

        # Calculate performance metrics
        performance_data = []
        for symbol, data in symbol_data.items():
            avg_price_change = sum(data['price_changes']) / len(data['price_changes'])
            avg_volume = sum(data['volumes']) / len(data['volumes'])
            avg_market_cap = sum(data['market_caps']) / len(data['market_caps'])
            
            performance_data.append({
                'symbol': symbol,
                'price_change': avg_price_change,
                'volume': avg_volume,
                'market_cap': avg_market_cap
            })

        # Sort by price change to get top gainers and losers
        performance_data.sort(key=lambda x: x['price_change'], reverse=True)
        top_gainers = performance_data[:self.top_limit]
        top_losers = performance_data[-self.top_limit:][::-1]

        # Calculate market summary
        total_market_cap = sum(data['market_cap'] for data in performance_data)
        total_volume = sum(data['volume'] for data in performance_data)
        avg_price_change = sum(data['price_change'] for data in performance_data) / len(performance_data)

        market_summary = {
            'total_market_cap': total_market_cap,
            'total_volume': total_volume,
            'average_price_change': avg_price_change,
            'total_coins': len(performance_data)
        }

        # Create report
        report = await MarketReport.create(
            report_type=report_type,
            start_date=start_date,
            end_date=end_date,
            top_gainers=top_gainers,
            top_losers=top_losers,
            market_summary=market_summary
        )

        await cache_service.set(cache_key, json.dumps(report.to_dict()), expire=self.cache_ttl)
        return report

    async def get_latest_report(self, report_type: str = "daily") -> Optional[MarketReport]:
        """Get the latest market report"""
        report = await MarketReport.filter(
            report_type=report_type
        ).order_by("-created_at").first()
        return report

    async def create_market_alert(
        self,
        user: User,
        symbol: str,
        alert_type: str,
        threshold: Decimal
    ) -> UserMarketAlert:
        """Create a new market alert for a user"""
        alert = await UserMarketAlert.create(
            user=user,
            symbol=symbol,
            alert_type=alert_type,
            threshold=threshold
        )
        return alert

    async def check_market_alerts(self):
        """Check and trigger market alerts"""
        active_alerts = await UserMarketAlert.filter(is_active=True)
        latest_data = await MarketData.filter().order_by("-last_updated").first()

        if not latest_data:
            return

        for alert in active_alerts:
            try:
                if alert.symbol == latest_data.symbol:
                    if alert.alert_type == "price_increase" and latest_data.price_change_24h >= alert.threshold:
                        await self._trigger_alert(alert, latest_data)
                    elif alert.alert_type == "price_decrease" and latest_data.price_change_24h <= -alert.threshold:
                        await self._trigger_alert(alert, latest_data)
                    elif alert.alert_type == "volume_increase" and latest_data.volume_24h >= alert.threshold:
                        await self._trigger_alert(alert, latest_data)
            except Exception as e:
                logger.error(f"Error checking alert {alert.id}: {str(e)}")

    async def _trigger_alert(self, alert: UserMarketAlert, market_data: MarketData):
        """Trigger an alert and update its status"""
        alert.last_triggered = datetime.now()
        await alert.save()

        # Here you would implement the actual alert notification
        # For example, send an email, push notification, etc.
        logger.info(f"Alert triggered for user {alert.user_id}: {alert.symbol} {alert.alert_type}")

market_report_service = MarketReportService() 