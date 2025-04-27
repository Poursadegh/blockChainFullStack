from decimal import Decimal
from typing import List, Optional, Tuple
from datetime import datetime, timedelta
from ..models.trading import Order, Trade, OrderBook, OrderType, OrderStatus
from ..models.user import User
from .cache import cache_service
import asyncio
from fastapi import WebSocket
import json

class MatchingEngine:
    def __init__(self):
        self.active_orders: List[Order] = []
        self.websocket_connections: List[WebSocket] = []
        self.lock = asyncio.Lock()

    async def add_websocket_connection(self, websocket: WebSocket):
        self.websocket_connections.append(websocket)

    async def remove_websocket_connection(self, websocket: WebSocket):
        if websocket in self.websocket_connections:
            self.websocket_connections.remove(websocket)

    async def broadcast_trade(self, trade: Trade):
        message = {
            "type": "trade",
            "data": {
                "id": trade.id,
                "symbol": trade.symbol,
                "price": str(trade.price),
                "amount": str(trade.amount),
                "buyer_id": trade.buyer_id,
                "seller_id": trade.seller_id,
                "timestamp": trade.created_at.isoformat()
            }
        }
        for connection in self.websocket_connections:
            try:
                await connection.send_json(message)
            except:
                await self.remove_websocket_connection(connection)

    async def broadcast_order_book(self, symbol: str):
        order_book = await self.get_order_book(symbol)
        message = {
            "type": "order_book",
            "data": order_book
        }
        for connection in self.websocket_connections:
            try:
                await connection.send_json(message)
            except:
                await self.remove_websocket_connection(connection)

    async def place_order(self, order: Order) -> List[Trade]:
        async with self.lock:
            trades = []
            remaining_amount = order.amount - order.filled_amount

            # Get matching orders
            matching_orders = await self._get_matching_orders(order)
            
            for matching_order in matching_orders:
                if remaining_amount <= 0:
                    break

                # Calculate trade amount
                trade_amount = min(
                    remaining_amount,
                    matching_order.amount - matching_order.filled_amount
                )

                # Calculate trade price
                trade_price = matching_order.price

                # Create trade
                trade = await Trade.create(
                    symbol=order.symbol,
                    buyer=order.user if order.order_type == OrderType.BUY else matching_order.user,
                    seller=order.user if order.order_type == OrderType.SELL else matching_order.user,
                    price=trade_price,
                    amount=trade_amount,
                    buy_order=order if order.order_type == OrderType.BUY else matching_order,
                    sell_order=order if order.order_type == OrderType.SELL else matching_order
                )

                # Update order filled amounts
                order.filled_amount += trade_amount
                matching_order.filled_amount += trade_amount

                # Update order statuses
                if order.filled_amount == order.amount:
                    order.status = OrderStatus.FILLED
                else:
                    order.status = OrderStatus.PARTIALLY_FILLED

                if matching_order.filled_amount == matching_order.amount:
                    matching_order.status = OrderStatus.FILLED
                else:
                    matching_order.status = OrderStatus.PARTIALLY_FILLED

                # Save order updates
                await order.save()
                await matching_order.save()

                # Update order book
                await self._update_order_book(order.symbol, trade_price, trade_amount)

                trades.append(trade)
                remaining_amount -= trade_amount

                # Broadcast trade
                await self.broadcast_trade(trade)

            # If order is not fully filled, add to active orders
            if remaining_amount > 0:
                self.active_orders.append(order)

            # Broadcast updated order book
            await self.broadcast_order_book(order.symbol)

            return trades

    async def _get_matching_orders(self, order: Order) -> List[Order]:
        if order.order_type == OrderType.BUY:
            return [
                o for o in self.active_orders
                if o.symbol == order.symbol
                and o.order_type == OrderType.SELL
                and o.price <= order.price
                and o.status == OrderStatus.PENDING
            ]
        else:
            return [
                o for o in self.active_orders
                if o.symbol == order.symbol
                and o.order_type == OrderType.BUY
                and o.price >= order.price
                and o.status == OrderStatus.PENDING
            ]

    async def _update_order_book(self, symbol: str, price: Decimal, amount: Decimal):
        order_book = await OrderBook.get_or_create(symbol=symbol)
        order_book = order_book[0]
        
        # Update last price
        order_book.last_price = price
        
        # Update 24h volume
        order_book.volume_24h += amount
        
        # Update 24h high/low
        if order_book.high_24h is None or price > order_book.high_24h:
            order_book.high_24h = price
        if order_book.low_24h is None or price < order_book.low_24h:
            order_book.low_24h = price
            
        await order_book.save()

    async def get_order_book(self, symbol: str) -> dict:
        # Try to get from cache first
        cached_data = await cache_service.get(f"order_book:{symbol}")
        if cached_data:
            return json.loads(cached_data)

        # Get from database
        order_book = await OrderBook.get_or_create(symbol=symbol)
        order_book = order_book[0]

        # Get active orders
        buy_orders = [
            {
                "price": str(o.price),
                "amount": str(o.amount - o.filled_amount)
            }
            for o in self.active_orders
            if o.symbol == symbol
            and o.order_type == OrderType.BUY
            and o.status == OrderStatus.PENDING
        ]

        sell_orders = [
            {
                "price": str(o.price),
                "amount": str(o.amount - o.filled_amount)
            }
            for o in self.active_orders
            if o.symbol == symbol
            and o.order_type == OrderType.SELL
            and o.status == OrderStatus.PENDING
        ]

        data = {
            "symbol": symbol,
            "last_price": str(order_book.last_price) if order_book.last_price else None,
            "volume_24h": str(order_book.volume_24h),
            "high_24h": str(order_book.high_24h) if order_book.high_24h else None,
            "low_24h": str(order_book.low_24h) if order_book.low_24h else None,
            "bids": sorted(buy_orders, key=lambda x: float(x["price"]), reverse=True),
            "asks": sorted(sell_orders, key=lambda x: float(x["price"]))
        }

        # Cache the result
        await cache_service.set(f"order_book:{symbol}", json.dumps(data), expire=1)

        return data

    async def cancel_order(self, order_id: int, user_id: int) -> bool:
        async with self.lock:
            order = await Order.get_or_none(id=order_id, user_id=user_id)
            if not order or order.status not in [OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED]:
                return False

            order.status = OrderStatus.CANCELLED
            await order.save()

            if order in self.active_orders:
                self.active_orders.remove(order)

            # Broadcast updated order book
            await self.broadcast_order_book(order.symbol)

            return True

matching_engine = MatchingEngine() 