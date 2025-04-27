from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from enum import Enum

class TransactionType(str, Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRADE = "trade"

class WalletBase(BaseModel):
    currency: str
    balance: float = 0.0

class WalletCreate(WalletBase):
    user_id: int

class WalletUpdate(WalletBase):
    pass

class WalletInDB(WalletBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TransactionBase(BaseModel):
    type: TransactionType
    amount: float
    price: Optional[float] = None
    currency: str

class TransactionCreate(TransactionBase):
    wallet_id: int

class TransactionUpdate(BaseModel):
    status: str
    completed_at: Optional[datetime] = None

class TransactionInDB(TransactionBase):
    id: int
    wallet_id: int
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True 