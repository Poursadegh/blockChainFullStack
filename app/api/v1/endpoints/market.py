from fastapi import APIRouter, Depends, HTTPException, WebSocket
from typing import List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from pydantic import BaseModel
from ...models.market import MarketPrice, HistoricalPrice, MarketNews, MarketAnalysis
from ...services.market import market_service
from ...core.security import get_current_user
from ...models.user import User

router = APIRouter()

class PriceResponse(BaseModel):
    symbol: str
    price: Decimal
    volume_24h: Decimal
    change_24h: Decimal
    high_24h: Decimal
    low_24h: Decimal
    timestamp: datetime

class HistoricalPriceResponse(BaseModel):
    symbol: str
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: Decimal
    interval: str
    timestamp: datetime

class TechnicalAnalysisResponse(BaseModel):
    symbol: str
    trend: str
    rsi: float
    rsi_signal: str
    chart: str
    indicators: dict
    timeframe: str

class MarketNewsResponse(BaseModel):
    id: int
    title: str
    content: str
    source: str
    url: str
    sentiment: Optional[str]
    impact: Optional[str]
    symbols: List[str]
    published_at: datetime

@router.get("/price/{symbol}", response_model=PriceResponse)
async def get_price(symbol: str):
    price = await market_service.get_current_price(symbol)
    if not price:
        raise HTTPException(status_code=404, detail="Price not found")
    return price

@router.get("/historical/{symbol}", response_model=List[HistoricalPriceResponse])
async def get_historical_prices(
    symbol: str,
    interval: str = "1h",
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
):
    if not start_time:
        start_time = datetime.now() - timedelta(days=30)
    if not end_time:
        end_time = datetime.now()
    
    prices = await market_service.get_historical_prices(
        symbol=symbol,
        interval=interval,
        start_time=start_time,
        end_time=end_time
    )
    return prices

@router.get("/analysis/{symbol}", response_model=TechnicalAnalysisResponse)
async def get_technical_analysis(
    symbol: str,
    interval: str = "1h",
    timeframe: str = "1d"
):
    analysis = await market_service.generate_technical_analysis(
        symbol=symbol,
        interval=interval,
        timeframe=timeframe
    )
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis

@router.get("/news", response_model=List[MarketNewsResponse])
async def get_news(
    symbols: Optional[List[str]] = None,
    limit: int = 10
):
    news = await market_service.get_market_news(symbols=symbols, limit=limit)
    return news

@router.websocket("/ws/price/{symbol}")
async def websocket_price(websocket: WebSocket, symbol: str):
    await websocket.accept()
    await market_service.add_websocket_connection(websocket)
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except:
        await market_service.remove_websocket_connection(websocket)
        await websocket.close()

@router.get("/analysis/history/{symbol}")
async def get_analysis_history(
    symbol: str,
    analysis_type: str = "technical",
    timeframe: str = "1d",
    limit: int = 10
):
    analysis = await MarketAnalysis.filter(
        symbol=symbol,
        analysis_type=analysis_type,
        timeframe=timeframe
    ).order_by("-created_at").limit(limit)
    return analysis 