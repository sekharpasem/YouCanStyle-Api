from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class PaymentMethod(str, Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    UPI = "upi"
    NETBANKING = "netbanking"
    WALLET = "wallet"
    CASH = "cash"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"

class TransactionType(str, Enum):
    PAYMENT = "payment"
    REFUND = "refund"
    PAYOUT = "payout"
    WITHDRAWAL = "withdrawal"
    DEPOSIT = "deposit"
    FEE = "fee"
    TAX = "tax"

class PaymentCreate(BaseModel):
    bookingId: str
    amount: float
    currency: str = "INR"
    paymentMethod: PaymentMethod
    metadata: Optional[Dict[str, Any]] = None

class PaymentResponse(BaseModel):
    id: str
    bookingId: str
    clientId: str
    stylistId: str
    amount: float
    currency: str = "INR"
    paymentMethod: PaymentMethod
    status: PaymentStatus
    transactionId: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    createdAt: datetime
    updatedAt: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class PaymentMethodCreate(BaseModel):
    userId: str
    type: PaymentMethod
    cardNumber: Optional[str] = None
    cardExpiry: Optional[str] = None
    cardHolderName: Optional[str] = None
    upiId: Optional[str] = None
    bankName: Optional[str] = None
    bankAccountNumber: Optional[str] = None
    ifscCode: Optional[str] = None
    isDefault: bool = False
    metadata: Optional[Dict[str, Any]] = None

class PaymentMethodResponse(BaseModel):
    id: str
    userId: str
    type: PaymentMethod
    lastFour: Optional[str] = None
    cardBrand: Optional[str] = None
    cardExpiry: Optional[str] = None
    cardHolderName: Optional[str] = None
    upiId: Optional[str] = None
    bankName: Optional[str] = None
    bankAccountLast4: Optional[str] = None
    isDefault: bool = False
    createdAt: datetime
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class PayoutCreate(BaseModel):
    stylistId: str
    amount: float
    currency: str = "INR"
    bankAccountId: str
    description: Optional[str] = None

class PayoutResponse(BaseModel):
    id: str
    stylistId: str
    amount: float
    currency: str = "INR"
    status: PaymentStatus
    bankAccountId: str
    description: Optional[str] = None
    transactionId: Optional[str] = None
    createdAt: datetime
    processedAt: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class TransactionResponse(BaseModel):
    id: str
    userId: str
    type: TransactionType
    amount: float
    currency: str = "INR"
    status: PaymentStatus
    description: str
    bookingId: Optional[str] = None
    paymentId: Optional[str] = None
    payoutId: Optional[str] = None
    fee: Optional[float] = None
    tax: Optional[float] = None
    createdAt: datetime
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class PaymentStatistics(BaseModel):
    totalEarnings: float = 0
    pendingPayouts: float = 0
    completedBookings: int = 0
    totalBookings: int = 0
    
    class Config:
        populate_by_name = True
