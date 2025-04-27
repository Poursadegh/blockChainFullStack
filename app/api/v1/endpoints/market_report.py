from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from datetime import datetime
from ...models.market_report import MarketData, MarketReport, UserMarketAlert
from ...models.user import User
from ...services.market_report import market_report_service
from ...core.security import get_current_user
from pydantic import BaseModel
from decimal import Decimal

router = APIRouter()

class MarketAlertCreate(BaseModel):
    symbol: str
    alert_type: str
    threshold: Decimal

class MarketDataResponse(BaseModel):
    symbol: str
    price: Decimal
    volume_24h: Decimal
    market_cap: Decimal
    price_change_24h: Decimal
    price_change_7d: Decimal
    last_updated: datetime

    class Config:
        orm_mode = True

class MarketReportResponse(BaseModel):
    report_type: str
    start_date: datetime
    end_date: datetime
    top_gainers: List[dict]
    top_losers: List[dict]
    market_summary: dict
    created_at: datetime

    class Config:
        orm_mode = True

@router.get("/market-data", response_model=List[MarketDataResponse])
async def get_market_data():
    """Get latest market data for all cryptocurrencies"""
    market_data = await market_report_service.fetch_market_data()
    return market_data

@router.get("/reports/{report_type}", response_model=MarketReportResponse)
async def get_market_report(report_type: str = "daily"):
    """Get the latest market report"""
    report = await market_report_service.get_latest_report(report_type)
    if not report:
        report = await market_report_service.generate_market_report(report_type)
    return report

@router.get("/top-gainers", response_model=List[MarketDataResponse])
async def get_top_gainers(limit: int = 10):
    """Get top performing cryptocurrencies"""
    market_data = await MarketData.filter().order_by("-price_change_24h").limit(limit)
    return market_data

@router.get("/top-losers", response_model=List[MarketDataResponse])
async def get_top_losers(limit: int = 10):
    """Get worst performing cryptocurrencies"""
    market_data = await MarketData.filter().order_by("price_change_24h").limit(limit)
    return market_data

@router.post("/alerts", response_model=UserMarketAlert)
async def create_market_alert(
    alert_data: MarketAlertCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new market alert"""
    alert = await market_report_service.create_market_alert(
        user=current_user,
        symbol=alert_data.symbol,
        alert_type=alert_data.alert_type,
        threshold=alert_data.threshold
    )
    return alert

@router.get("/alerts", response_model=List[UserMarketAlert])
async def get_user_alerts(current_user: User = Depends(get_current_user)):
    """Get all alerts for the current user"""
    alerts = await UserMarketAlert.filter(user=current_user)
    return alerts

@router.delete("/alerts/{alert_id}")
async def delete_market_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user)
):
    """Delete a market alert"""
    alert = await UserMarketAlert.get_or_none(id=alert_id, user=current_user)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    await alert.delete()
    return {"status": "success", "message": "Alert deleted successfully"}

@router.get("/market-summary")
async def get_market_summary():
    """Get overall market summary"""
    report = await market_report_service.get_latest_report()
    if not report:
        report = await market_report_service.generate_market_report()
    
    return {
        "total_market_cap": report.market_summary["total_market_cap"],
        "total_volume": report.market_summary["total_volume"],
        "average_price_change": report.market_summary["average_price_change"],
        "total_coins": report.market_summary["total_coins"],
        "top_gainers": report.top_gainers[:5],
        "top_losers": report.top_losers[:5]
    } 