from typing import List, Optional, Dict
from decimal import Decimal
from datetime import datetime
from cryptography.fernet import Fernet
from ..models.wallet import Wallet, WalletAddress, Transaction, WalletBackup, WalletType, WalletStatus
from ..models.user import User
from .cache import cache_service
import json
import asyncio
from fastapi import WebSocket

class WalletService:
    def __init__(self):
        self.encryption_key = Fernet.generate_key()
        self.cipher_suite = Fernet(self.encryption_key)
        self.websocket_connections: List[WebSocket] = []

    async def add_websocket_connection(self, websocket: WebSocket):
        self.websocket_connections.append(websocket)

    async def remove_websocket_connection(self, websocket: WebSocket):
        if websocket in self.websocket_connections:
            self.websocket_connections.remove(websocket)

    async def broadcast_balance_update(self, user_id: int, currency: str, balance: Decimal):
        message = {
            "type": "balance_update",
            "data": {
                "user_id": user_id,
                "currency": currency,
                "balance": str(balance)
            }
        }
        for connection in self.websocket_connections:
            try:
                await connection.send_json(message)
            except:
                await self.remove_websocket_connection(connection)

    def _encrypt_data(self, data: str) -> str:
        return self.cipher_suite.encrypt(data.encode()).decode()

    def _decrypt_data(self, encrypted_data: str) -> str:
        return self.cipher_suite.decrypt(encrypted_data.encode()).decode()

    async def create_wallet(
        self,
        user: User,
        name: str,
        wallet_type: WalletType,
        currency: str,
        address: str,
        public_key: str,
        private_key: Optional[str] = None
    ) -> Wallet:
        # Create wallet
        wallet = await Wallet.create(
            user=user,
            name=name,
            wallet_type=wallet_type,
            status=WalletStatus.ACTIVE
        )

        # Create wallet address
        await WalletAddress.create(
            wallet=wallet,
            currency=currency,
            address=address,
            public_key=public_key,
            private_key=self._encrypt_data(private_key) if private_key else None,
            is_default=True
        )

        return wallet

    async def add_address(
        self,
        wallet: Wallet,
        currency: str,
        address: str,
        public_key: str,
        private_key: Optional[str] = None
    ) -> WalletAddress:
        return await WalletAddress.create(
            wallet=wallet,
            currency=currency,
            address=address,
            public_key=public_key,
            private_key=self._encrypt_data(private_key) if private_key else None
        )

    async def get_wallet_balance(self, wallet: Wallet, currency: str) -> Decimal:
        # Try to get from cache first
        cache_key = f"wallet_balance:{wallet.id}:{currency}"
        cached_balance = await cache_service.get(cache_key)
        if cached_balance:
            return Decimal(cached_balance)

        # Get from database
        address = await WalletAddress.filter(
            wallet=wallet,
            currency=currency,
            is_default=True
        ).first()

        if not address:
            return Decimal(0)

        # Cache the result
        await cache_service.set(cache_key, str(address.balance), expire=60)

        return address.balance

    async def update_balance(
        self,
        wallet: Wallet,
        currency: str,
        amount: Decimal,
        transaction_type: str,
        tx_hash: str,
        fee: Decimal = Decimal(0),
        from_address: Optional[str] = None,
        to_address: Optional[str] = None
    ) -> Transaction:
        async with asyncio.Lock():
            address = await WalletAddress.filter(
                wallet=wallet,
                currency=currency,
                is_default=True
            ).first()

            if not address:
                raise ValueError(f"No address found for currency {currency}")

            # Update balance
            address.balance += amount
            await address.save()

            # Create transaction record
            transaction = await Transaction.create(
                wallet=wallet,
                address=address,
                tx_hash=tx_hash,
                amount=amount,
                fee=fee,
                currency=currency,
                status="completed",
                type=transaction_type,
                from_address=from_address,
                to_address=to_address
            )

            # Update cache
            cache_key = f"wallet_balance:{wallet.id}:{currency}"
            await cache_service.set(cache_key, str(address.balance), expire=60)

            # Broadcast balance update
            await self.broadcast_balance_update(wallet.user_id, currency, address.balance)

            return transaction

    async def create_backup(
        self,
        wallet: Wallet,
        backup_data: str,
        backup_type: str
    ) -> WalletBackup:
        encrypted_data = self._encrypt_data(backup_data)
        return await WalletBackup.create(
            wallet=wallet,
            backup_data=encrypted_data,
            backup_type=backup_type
        )

    async def get_backup(self, backup_id: int, wallet: Wallet) -> Optional[str]:
        backup = await WalletBackup.get_or_none(id=backup_id, wallet=wallet)
        if backup:
            return self._decrypt_data(backup.backup_data)
        return None

    async def get_wallet_transactions(
        self,
        wallet: Wallet,
        currency: Optional[str] = None,
        limit: int = 50
    ) -> List[Transaction]:
        query = Transaction.filter(wallet=wallet)
        if currency:
            query = query.filter(currency=currency)
        
        return await query.order_by("-created_at").limit(limit)

    async def lock_wallet(self, wallet: Wallet) -> bool:
        if wallet.status == WalletStatus.ACTIVE:
            wallet.status = WalletStatus.LOCKED
            await wallet.save()
            return True
        return False

    async def unlock_wallet(self, wallet: Wallet) -> bool:
        if wallet.status == WalletStatus.LOCKED:
            wallet.status = WalletStatus.ACTIVE
            await wallet.save()
            return True
        return False

    async def get_wallet_addresses(self, wallet: Wallet) -> List[WalletAddress]:
        return await WalletAddress.filter(wallet=wallet).all()

    async def get_wallet_backups(self, wallet: Wallet) -> List[WalletBackup]:
        return await WalletBackup.filter(wallet=wallet).all()

    async def get_wallet_summary(self, wallet: Wallet) -> Dict:
        addresses = await self.get_wallet_addresses(wallet)
        transactions = await self.get_wallet_transactions(wallet, limit=10)
        
        return {
            "wallet": {
                "id": wallet.id,
                "name": wallet.name,
                "type": wallet.wallet_type,
                "status": wallet.status,
                "created_at": wallet.created_at,
                "updated_at": wallet.updated_at
            },
            "addresses": [
                {
                    "id": addr.id,
                    "currency": addr.currency,
                    "address": addr.address,
                    "balance": str(addr.balance),
                    "is_default": addr.is_default
                }
                for addr in addresses
            ],
            "recent_transactions": [
                {
                    "id": tx.id,
                    "amount": str(tx.amount),
                    "currency": tx.currency,
                    "type": tx.type,
                    "status": tx.status,
                    "created_at": tx.created_at
                }
                for tx in transactions
            ]
        }

wallet_service = WalletService() 