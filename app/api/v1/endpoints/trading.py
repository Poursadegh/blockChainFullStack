from fastapi import APIRouter, WebSocket, Depends, HTTPException
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel, Field
from ...models.trading import Order, Trade, OrderType, OrderStatus
from ...services.matching import matching_engine
from ...core.auth import get_current_user
from ...models.user import User

router = APIRouter(
    prefix="/trading",
    tags=["trading"],
    responses={404: {"description": "Not found"}},
)

class OrderCreate(BaseModel):
    """Model for creating a new order"""
    symbol: str = Field(..., description="Trading pair symbol (e.g., 'BTC/USDT')", example="BTC/USDT")
    order_type: OrderType = Field(..., description="Type of order (buy or sell)")
    price: Decimal = Field(..., description="Order price", example="50000.00")
    amount: Decimal = Field(..., description="Order amount", example="0.1")

    class Config:
        schema_extra = {
            "example": {
                "symbol": "BTC/USDT",
                "order_type": "buy",
                "price": "50000.00",
                "amount": "0.1"
            }
        }

class OrderResponse(BaseModel):
    """Model for order response"""
    id: int = Field(..., description="Order ID")
    symbol: str = Field(..., description="Trading pair symbol")
    order_type: OrderType = Field(..., description="Type of order")
    price: Decimal = Field(..., description="Order price")
    amount: Decimal = Field(..., description="Order amount")
    filled_amount: Decimal = Field(..., description="Amount filled so far")
    status: OrderStatus = Field(..., description="Current order status")
    created_at: str = Field(..., description="Order creation timestamp")

class TradeResponse(BaseModel):
    """Model for trade response"""
    id: int = Field(..., description="Trade ID")
    symbol: str = Field(..., description="Trading pair symbol")
    price: Decimal = Field(..., description="Trade price")
    amount: Decimal = Field(..., description="Trade amount")
    buyer_id: int = Field(..., description="Buyer user ID")
    seller_id: int = Field(..., description="Seller user ID")
    timestamp: str = Field(..., description="Trade timestamp")

class OrderBookResponse(BaseModel):
    """Model for order book response"""
    symbol: str = Field(..., description="Trading pair symbol")
    last_price: Optional[str] = Field(None, description="Last trade price")
    volume_24h: str = Field(..., description="24-hour trading volume")
    high_24h: Optional[str] = Field(None, description="24-hour high price")
    low_24h: Optional[str] = Field(None, description="24-hour low price")
    bids: List[dict] = Field(..., description="Buy orders (price, amount)")
    asks: List[dict] = Field(..., description="Sell orders (price, amount)")

@router.websocket("/ws/trading/{symbol}")
async def trading_websocket(
    websocket: WebSocket,
    symbol: str = Field(..., description="Trading pair symbol (e.g., 'BTC/USDT')")
):
    """
    WebSocket endpoint for real-time trading updates.
    
    Subscribe to receive:
    - Real-time order book updates
    - Trade notifications
    - Market statistics
    
    Send a message with type "subscribe" to start receiving updates.
    """
    await websocket.accept()
    await matching_engine.add_websocket_connection(websocket)
    
    try:
        while True:
            data = await websocket.receive_json()
            if data["type"] == "subscribe":
                order_book = await matching_engine.get_order_book(symbol)
                await websocket.send_json({
                    "type": "order_book",
                    "data": order_book
                })
    except:
        await matching_engine.remove_websocket_connection(websocket)

@router.post(
    "/orders",
    response_model=OrderResponse,
    summary="Create a new order",
    description="Create a new buy or sell order for a trading pair",
    response_description="The created order details"
)
async def create_order(
    order_data: OrderCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new trading order.
    
    - **symbol**: Trading pair (e.g., BTC/USDT)
    - **order_type**: Type of order (buy or sell)
    - **price**: Order price
    - **amount**: Order amount
    
    Returns the created order details.
    """
    order = await Order.create(
        user=current_user,
        symbol=order_data.symbol,
        order_type=order_data.order_type,
        price=order_data.price,
        amount=order_data.amount
    )

    trades = await matching_engine.place_order(order)

    return {
        "id": order.id,
        "symbol": order.symbol,
        "order_type": order.order_type,
        "price": order.price,
        "amount": order.amount,
        "filled_amount": order.filled_amount,
        "status": order.status,
        "created_at": order.created_at.isoformat()
    }

@router.post(
    "/orders/{order_id}/cancel",
    summary="Cancel an order",
    description="Cancel a pending or partially filled order",
    responses={
        200: {"description": "Order cancelled successfully"},
        404: {"description": "Order not found or cannot be cancelled"}
    }
)
async def cancel_order(
    order_id: int = Field(..., description="ID of the order to cancel"),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel a trading order.
    
    - **order_id**: ID of the order to cancel
    
    Returns success status if the order was cancelled.
    """
    success = await matching_engine.cancel_order(order_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Order not found or cannot be cancelled")
    return {"status": "success"}

@router.get(
    "/orders",
    response_model=List[OrderResponse],
    summary="Get user orders",
    description="Retrieve a list of user's orders, optionally filtered by status"
)
async def get_user_orders(
    status: Optional[OrderStatus] = Field(None, description="Filter orders by status"),
    current_user: User = Depends(get_current_user)
):
    """
    Get a list of user's trading orders.
    
    - **status**: Optional filter for order status (pending, filled, cancelled, etc.)
    
    Returns a list of orders sorted by creation time (newest first).
    """
    query = Order.filter(user_id=current_user.id)
    if status:
        query = query.filter(status=status)
    
    orders = await query.order_by("-created_at")
    return [
        {
            "id": order.id,
            "symbol": order.symbol,
            "order_type": order.order_type,
            "price": order.price,
            "amount": order.amount,
            "filled_amount": order.filled_amount,
            "status": order.status,
            "created_at": order.created_at.isoformat()
        }
        for order in orders
    ]

@router.get(
    "/trades",
    response_model=List[TradeResponse],
    summary="Get user trades",
    description="Retrieve a list of user's trades, optionally filtered by symbol"
)
async def get_user_trades(
    symbol: Optional[str] = Field(None, description="Filter trades by trading pair"),
    current_user: User = Depends(get_current_user)
):
    """
    Get a list of user's trades.
    
    - **symbol**: Optional filter for trading pair
    
    Returns a list of trades sorted by time (newest first).
    """
    query = Trade.filter(
        (Trade.buyer_id == current_user.id) | (Trade.seller_id == current_user.id)
    )
    if symbol:
        query = query.filter(symbol=symbol)
    
    trades = await query.order_by("-created_at")
    return [
        {
            "id": trade.id,
            "symbol": trade.symbol,
            "price": trade.price,
            "amount": trade.amount,
            "buyer_id": trade.buyer_id,
            "seller_id": trade.seller_id,
            "timestamp": trade.created_at.isoformat()
        }
        for trade in trades
    ]

@router.get(
    "/orderbook/{symbol}",
    response_model=OrderBookResponse,
    summary="Get order book",
    description="Retrieve the current order book for a trading pair"
)
async def get_order_book(
    symbol: str = Field(..., description="Trading pair symbol (e.g., 'BTC/USDT')")
):
    """
    Get the current order book for a trading pair.
    
    - **symbol**: Trading pair symbol
    
    Returns the order book with:
    - Current bids and asks
    - Last price
    - 24-hour volume and price statistics
    """
    order_book = await matching_engine.get_order_book(symbol)
    return order_book 