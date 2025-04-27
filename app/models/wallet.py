from tortoise import fields
from tortoise.models import Model
from tortoise.contrib.pydantic import pydantic_model_creator
from enum import Enum
from datetime import datetime
from decimal import Decimal

class TransactionType(str, Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRADE = "trade"

class WalletType(str, Enum):
    HOT = "hot"  # Online wallet for frequent transactions
    COLD = "cold"  # Offline wallet for secure storage

class WalletStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"

class Wallet(Model):
    id = fields.BigIntField(pk=True)
    user = fields.ForeignKeyField('models.User', related_name='wallets')
    name = fields.CharField(max_length=100)
    wallet_type = fields.CharEnumField(WalletType)
    status = fields.CharEnumField(WalletStatus, default=WalletStatus.ACTIVE)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    # Reverse relations
    transactions: fields.ReverseRelation["Transaction"]
    addresses: fields.ReverseRelation["WalletAddress"]
    backups: fields.ReverseRelation["WalletBackup"]

    class Meta:
        table = "wallets"
        indexes = [("user_id", "wallet_type")]

    def __str__(self):
        return f"{self.name} wallet for {self.user.username}"

class WalletAddress(Model):
    id = fields.BigIntField(pk=True)
    wallet = fields.ForeignKeyField('models.Wallet', related_name='addresses')
    currency = fields.CharField(max_length=20)  # e.g., BTC, ETH, USDT
    address = fields.CharField(max_length=255, unique=True)
    private_key = fields.CharField(max_length=255, null=True)  # Encrypted
    public_key = fields.CharField(max_length=255)
    balance = fields.DecimalField(max_digits=30, decimal_places=18, default=0)
    is_default = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "wallet_addresses"
        indexes = [
            ("wallet_id", "currency"),
            ("address",)
        ]

class Transaction(Model):
    id = fields.BigIntField(pk=True)
    wallet = fields.ForeignKeyField('models.Wallet', related_name='transactions')
    address = fields.ForeignKeyField('models.WalletAddress', related_name='transactions')
    tx_hash = fields.CharField(max_length=255, unique=True)
    amount = fields.DecimalField(max_digits=30, decimal_places=18)
    fee = fields.DecimalField(max_digits=30, decimal_places=18, default=0)
    currency = fields.CharField(max_length=20)
    status = fields.CharField(max_length=20)  # pending, completed, failed
    type = fields.CharField(max_length=20)  # deposit, withdrawal, transfer
    from_address = fields.CharField(max_length=255, null=True)
    to_address = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "transactions"
        indexes = [
            ("wallet_id", "status"),
            ("tx_hash",),
            ("created_at",)
        ]

    def __str__(self):
        return f"{self.type} transaction of {self.amount} {self.currency}"

class WalletBackup(Model):
    id = fields.BigIntField(pk=True)
    wallet = fields.ForeignKeyField('models.Wallet', related_name='backups')
    backup_data = fields.TextField()  # Encrypted backup data
    backup_type = fields.CharField(max_length=20)  # seed phrase, private key, etc.
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "wallet_backups"
        indexes = [("wallet_id",)]

# Pydantic models
Wallet_Pydantic = pydantic_model_creator(Wallet, name="Wallet")
WalletIn_Pydantic = pydantic_model_creator(
    Wallet,
    name="WalletIn",
    exclude_readonly=True
)
WalletOut_Pydantic = pydantic_model_creator(Wallet, name="WalletOut")

Transaction_Pydantic = pydantic_model_creator(Transaction, name="Transaction")
TransactionIn_Pydantic = pydantic_model_creator(
    Transaction,
    name="TransactionIn",
    exclude_readonly=True
)
TransactionOut_Pydantic = pydantic_model_creator(Transaction, name="TransactionOut") 