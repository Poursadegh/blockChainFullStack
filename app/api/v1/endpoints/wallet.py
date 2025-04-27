from fastapi import APIRouter, WebSocket, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel, Field
from ...core.database import get_db
from ...models.wallet import Wallet, WalletAddress, Transaction, WalletBackup, WalletType, WalletStatus
from ...schemas.wallet import (
    WalletCreate,
    WalletInDB,
    TransactionCreate,
    TransactionInDB,
    TransactionUpdate
)
from ...services.trading_bot import TradingBot
from ...services.wallet import wallet_service
from ...core.auth import get_current_user
from ...models.user import User
from datetime import datetime

router = APIRouter(
    prefix="/wallets",
    tags=["wallets"],
    responses={404: {"description": "Not found"}},
)

class WalletCreate(BaseModel):
    """Model for creating a new wallet"""
    name: str = Field(..., description="Wallet name", example="My Trading Wallet")
    wallet_type: WalletType = Field(..., description="Type of wallet (hot or cold)")
    currency: str = Field(..., description="Currency code", example="BTC")
    address: str = Field(..., description="Wallet address")
    public_key: str = Field(..., description="Public key")
    private_key: Optional[str] = Field(None, description="Private key (encrypted)")

class WalletAddressCreate(BaseModel):
    """Model for adding a new address to a wallet"""
    currency: str = Field(..., description="Currency code", example="ETH")
    address: str = Field(..., description="Wallet address")
    public_key: str = Field(..., description="Public key")
    private_key: Optional[str] = Field(None, description="Private key (encrypted)")

class WalletBackupCreate(BaseModel):
    """Model for creating a wallet backup"""
    backup_data: str = Field(..., description="Backup data (seed phrase, private key, etc.)")
    backup_type: str = Field(..., description="Type of backup (seed_phrase, private_key, etc.)")

class DepositRequest(BaseModel):
    wallet_id: int
    currency: str
    amount: Decimal
    tx_hash: str
    from_address: Optional[str] = None

class WithdrawalRequest(BaseModel):
    wallet_id: int
    currency: str
    amount: Decimal
    to_address: str
    fee: Decimal = Decimal(0)

class BalanceResponse(BaseModel):
    currency: str
    balance: Decimal
    available_balance: Decimal

trading_bot = TradingBot()

@router.websocket("/ws/balance")
async def balance_websocket(websocket: WebSocket, current_user: User = Depends(get_current_user)):
    """
    WebSocket endpoint for real-time balance updates.
    
    Subscribe to receive:
    - Real-time balance updates for all currencies
    - Transaction notifications
    """
    await websocket.accept()
    await wallet_service.add_websocket_connection(websocket)
    
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except:
        await wallet_service.remove_websocket_connection(websocket)

@router.post("", response_model=Wallet)
async def create_wallet(
    wallet_data: WalletCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new wallet (hot or cold).
    
    - **name**: Wallet name
    - **wallet_type**: Type of wallet (hot or cold)
    - **currency**: Currency code
    - **address**: Wallet address
    - **public_key**: Public key
    - **private_key**: Optional private key (will be encrypted)
    """
    return await wallet_service.create_wallet(
        user=current_user,
        name=wallet_data.name,
        wallet_type=wallet_data.wallet_type,
        currency=wallet_data.currency,
        address=wallet_data.address,
        public_key=wallet_data.public_key,
        private_key=wallet_data.private_key
    )

@router.post("/{wallet_id}/addresses", response_model=WalletAddress)
async def add_wallet_address(
    wallet_id: int,
    address_data: WalletAddressCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Add a new address to an existing wallet.
    
    - **currency**: Currency code
    - **address**: Wallet address
    - **public_key**: Public key
    - **private_key**: Optional private key (will be encrypted)
    """
    wallet = await Wallet.get_or_none(id=wallet_id, user_id=current_user.id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    return await wallet_service.add_address(
        wallet=wallet,
        currency=address_data.currency,
        address=address_data.address,
        public_key=address_data.public_key,
        private_key=address_data.private_key
    )

@router.get("/{wallet_id}/balance/{currency}")
async def get_balance(
    wallet_id: int,
    currency: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get wallet balance for a specific currency.
    
    - **wallet_id**: Wallet ID
    - **currency**: Currency code
    """
    wallet = await Wallet.get_or_none(id=wallet_id, user_id=current_user.id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    balance = await wallet_service.get_wallet_balance(wallet, currency)
    return {"balance": str(balance)}

@router.get("/{wallet_id}/transactions")
async def get_transactions(
    wallet_id: int,
    currency: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user)
):
    """
    Get wallet transactions.
    
    - **wallet_id**: Wallet ID
    - **currency**: Optional currency filter
    - **limit**: Maximum number of transactions to return
    """
    wallet = await Wallet.get_or_none(id=wallet_id, user_id=current_user.id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    transactions = await wallet_service.get_wallet_transactions(wallet, currency, limit)
    return [
        {
            "id": tx.id,
            "tx_hash": tx.tx_hash,
            "amount": str(tx.amount),
            "fee": str(tx.fee),
            "currency": tx.currency,
            "type": tx.type,
            "status": tx.status,
            "from_address": tx.from_address,
            "to_address": tx.to_address,
            "timestamp": tx.created_at.isoformat()
        }
        for tx in transactions
    ]

@router.post("/{wallet_id}/backup", response_model=WalletBackup)
async def create_backup(
    wallet_id: int,
    backup_data: WalletBackupCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Create a wallet backup.
    
    - **backup_data**: Backup data (seed phrase, private key, etc.)
    - **backup_type**: Type of backup
    """
    wallet = await Wallet.get_or_none(id=wallet_id, user_id=current_user.id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    return await wallet_service.create_backup(
        wallet=wallet,
        backup_data=backup_data.backup_data,
        backup_type=backup_data.backup_type
    )

@router.get("/{wallet_id}/backup/{backup_id}")
async def get_backup(
    wallet_id: int,
    backup_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    Get wallet backup data.
    
    - **wallet_id**: Wallet ID
    - **backup_id**: Backup ID
    """
    wallet = await Wallet.get_or_none(id=wallet_id, user_id=current_user.id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    backup_data = await wallet_service.get_backup(backup_id, wallet)
    if not backup_data:
        raise HTTPException(status_code=404, detail="Backup not found")
    
    return {"backup_data": backup_data}

@router.post("/{wallet_id}/lock")
async def lock_wallet(
    wallet_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    Lock a wallet to prevent transactions.
    
    - **wallet_id**: Wallet ID
    """
    wallet = await Wallet.get_or_none(id=wallet_id, user_id=current_user.id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    success = await wallet_service.lock_wallet(wallet)
    if not success:
        raise HTTPException(status_code=400, detail="Wallet is not active")
    
    return {"status": "success"}

@router.post("/{wallet_id}/unlock")
async def unlock_wallet(
    wallet_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    Unlock a wallet to allow transactions.
    
    - **wallet_id**: Wallet ID
    """
    wallet = await Wallet.get_or_none(id=wallet_id, user_id=current_user.id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    success = await wallet_service.unlock_wallet(wallet)
    if not success:
        raise HTTPException(status_code=400, detail="Wallet is not locked")
    
    return {"status": "success"}

@router.get("/", response_model=List[WalletInDB])
async def get_user_wallets(user_id: int, db: Session = Depends(get_db)):
    wallets = db.query(Wallet).filter(Wallet.user_id == user_id).all()
    return wallets

@router.post("/deposit")
async def deposit_funds(
    request: DepositRequest,
    current_user: User = Depends(get_current_user)
):
    wallet = await Wallet.get_or_none(id=request.wallet_id, user=current_user)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    if wallet.status != WalletStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Wallet is not active")
    
    try:
        transaction = await wallet_service.update_balance(
            wallet=wallet,
            currency=request.currency,
            amount=request.amount,
            transaction_type="deposit",
            tx_hash=request.tx_hash,
            from_address=request.from_address
        )
        return {"message": "Deposit successful", "transaction": transaction}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/withdraw")
async def withdraw_funds(
    request: WithdrawalRequest,
    current_user: User = Depends(get_current_user)
):
    wallet = await Wallet.get_or_none(id=request.wallet_id, user=current_user)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    if wallet.status != WalletStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Wallet is not active")
    
    # Check if sufficient balance exists
    current_balance = await wallet_service.get_wallet_balance(wallet, request.currency)
    if current_balance < (request.amount + request.fee):
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    try:
        # Create withdrawal transaction
        transaction = await wallet_service.update_balance(
            wallet=wallet,
            currency=request.currency,
            amount=-request.amount,  # Negative amount for withdrawal
            transaction_type="withdrawal",
            tx_hash=f"withdraw_{request.wallet_id}_{request.currency}_{request.amount}",
            fee=request.fee,
            to_address=request.to_address
        )
        return {"message": "Withdrawal successful", "transaction": transaction}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/balance/{wallet_id}/{currency}")
async def get_wallet_balance(
    wallet_id: int,
    currency: str,
    current_user: User = Depends(get_current_user)
):
    wallet = await Wallet.get_or_none(id=wallet_id, user=current_user)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    balance = await wallet_service.get_wallet_balance(wallet, currency)
    return BalanceResponse(
        currency=currency,
        balance=balance,
        available_balance=balance if wallet.status == WalletStatus.ACTIVE else Decimal(0)
    )

@router.websocket("/ws/balance/{wallet_id}")
async def websocket_balance(
    websocket: WebSocket,
    wallet_id: int,
    current_user: User = Depends(get_current_user)
):
    await websocket.accept()
    await wallet_service.add_websocket_connection(websocket)
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except:
        await wallet_service.remove_websocket_connection(websocket)
        await websocket.close()

@router.get("/transactions/{wallet_id}")
async def get_wallet_transactions(
    wallet_id: int,
    currency: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user)
):
    wallet = await Wallet.get_or_none(id=wallet_id, user=current_user)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    transactions = await wallet_service.get_wallet_transactions(
        wallet=wallet,
        currency=currency,
        limit=limit
    )
    return transactions

@router.post("/{wallet_id}/trade", response_model=TransactionInDB)
async def execute_trade(
    wallet_id: int,
    symbol: str,
    strategy: str,
    amount: float,
    db: Session = Depends(get_db)
):
    wallet = db.query(Wallet).filter(Wallet.id == wallet_id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    try:
        trade_result = await trading_bot.execute_trade(symbol, strategy, amount)
        
        transaction = Transaction(
            wallet_id=wallet_id,
            type=TransactionType.TRADE,
            amount=amount,
            currency=wallet.currency,
            price=trade_result.get('price'),
            status="completed" if trade_result['action'] != 'hold' else "pending"
        )
        
        if trade_result['action'] == 'buy':
            wallet.balance -= amount
        elif trade_result['action'] == 'sell':
            wallet.balance += amount
        
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
        return transaction
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/portfolio/{user_id}")
async def get_portfolio_value(user_id: int):
    try:
        portfolio = await trading_bot.get_portfolio_value()
        return {
            "user_id": user_id,
            "portfolio": portfolio,
            "total_value": sum(portfolio.values()),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) 