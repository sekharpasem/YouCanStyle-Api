from typing import Dict, Any, List, Optional
from app.db.mongodb import db
from app.schemas.payment import (
    PaymentCreate, PaymentStatus, PaymentMethod,
    PaymentMethodCreate, PayoutCreate, TransactionType
)
from app.services.booking_service import get_booking_by_id
from app.services.notification_service import create_notification
from app.schemas.notification import NotificationCreate, NotificationType
from datetime import datetime
from bson import ObjectId
import logging
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock payment gateway client
class MockPaymentGateway:
    async def create_payment(self, amount, currency, payment_method, metadata=None):
        # Simulate payment processing
        transaction_id = f"txn_{uuid.uuid4().hex[:10]}"
        return {
            "id": transaction_id,
            "amount": amount,
            "currency": currency,
            "status": "completed",
            "created": datetime.utcnow().isoformat()
        }
        
    async def create_refund(self, payment_id, amount=None):
        # Simulate refund processing
        refund_id = f"ref_{uuid.uuid4().hex[:10]}"
        return {
            "id": refund_id,
            "payment_id": payment_id,
            "amount": amount,
            "status": "completed",
            "created": datetime.utcnow().isoformat()
        }
        
    async def create_payout(self, bank_account, amount, currency, description=None):
        # Simulate payout processing
        payout_id = f"po_{uuid.uuid4().hex[:10]}"
        return {
            "id": payout_id,
            "amount": amount,
            "currency": currency,
            "status": "pending",  # Payouts are typically not instant
            "created": datetime.utcnow().isoformat()
        }

# Initialize mock payment gateway
payment_gateway = MockPaymentGateway()

# Platform fee percentage
PLATFORM_FEE_PERCENTAGE = 10

async def create_payment(payment_in: PaymentCreate, client_id: str) -> Dict[str, Any]:
    """
    Create a new payment for a booking
    """
    # Get booking
    booking = await get_booking_by_id(payment_in.bookingId)
    if not booking:
        return None
        
    # Check if booking belongs to client
    if booking["clientId"] != client_id:
        return None
        
    # Create payment data
    payment_data = payment_in.dict()
    payment_data["clientId"] = client_id
    payment_data["stylistId"] = booking["stylistId"]
    payment_data["status"] = PaymentStatus.PENDING
    payment_data["createdAt"] = datetime.utcnow()
    
    # Calculate platform fee
    payment_data["platformFee"] = round(payment_in.amount * (PLATFORM_FEE_PERCENTAGE / 100), 2)
    payment_data["stylistAmount"] = payment_in.amount - payment_data["platformFee"]
    
    try:
        # Process payment with payment gateway
        # In production, this would integrate with a real payment processor
        payment_result = await payment_gateway.create_payment(
            payment_in.amount,
            payment_in.currency,
            payment_in.paymentMethod.value,
            metadata={"bookingId": payment_in.bookingId}
        )
        
        # Update payment with transaction ID
        payment_data["transactionId"] = payment_result["id"]
        payment_data["status"] = PaymentStatus.COMPLETED
        payment_data["updatedAt"] = datetime.utcnow()
        
        # Insert payment into database
        result = await db.db.payments.insert_one(payment_data)
        
        # Get the created payment
        created_payment = await db.db.payments.find_one({"_id": result.inserted_id})
        
        # Transform the _id field to string
        created_payment["id"] = str(created_payment["_id"])
        
        # Create transaction record
        transaction_data = {
            "userId": client_id,
            "type": TransactionType.PAYMENT,
            "amount": payment_in.amount,
            "currency": payment_in.currency,
            "status": PaymentStatus.COMPLETED,
            "description": f"Payment for booking #{payment_in.bookingId}",
            "bookingId": payment_in.bookingId,
            "paymentId": str(result.inserted_id),
            "fee": payment_data["platformFee"],
            "createdAt": datetime.utcnow()
        }
        
        await db.db.transactions.insert_one(transaction_data)
        
        # Create fee transaction
        fee_transaction = {
            "userId": "platform",
            "type": TransactionType.FEE,
            "amount": payment_data["platformFee"],
            "currency": payment_in.currency,
            "status": PaymentStatus.COMPLETED,
            "description": f"Platform fee for booking #{payment_in.bookingId}",
            "bookingId": payment_in.bookingId,
            "paymentId": str(result.inserted_id),
            "createdAt": datetime.utcnow()
        }
        
        await db.db.transactions.insert_one(fee_transaction)
        
        # Update booking payment status
        await db.db.bookings.update_one(
            {"_id": ObjectId(payment_in.bookingId)},
            {"$set": {"paymentStatus": PaymentStatus.COMPLETED}}
        )
        
        # Send notification to stylist
        notification = NotificationCreate(
            userId=booking["stylistId"],
            type=NotificationType.PAYMENT_RECEIVED,
            title="Payment Received",
            message=f"You've received a payment of {payment_in.currency} {payment_in.amount - payment_data['platformFee']} for booking #{payment_in.bookingId}",
            data={
                "bookingId": payment_in.bookingId,
                "amount": payment_in.amount - payment_data["platformFee"]
            }
        )
        
        await create_notification(notification)
        
        return created_payment
    
    except Exception as e:
        logger.error(f"Error processing payment: {str(e)}")
        
        # Create failed payment record
        payment_data["status"] = PaymentStatus.FAILED
        payment_data["errorMessage"] = str(e)
        payment_data["updatedAt"] = datetime.utcnow()
        
        await db.db.payments.insert_one(payment_data)
        
        return None

async def refund_payment(payment_id: str, reason: str = None) -> Dict[str, Any]:
    """
    Refund a payment
    """
    # Get payment
    payment = await get_payment_by_id(payment_id)
    if not payment:
        return None
        
    # Check if payment is completed
    if payment["status"] != PaymentStatus.COMPLETED:
        return None
        
    try:
        # Process refund with payment gateway
        refund_result = await payment_gateway.create_refund(
            payment["transactionId"],
            payment["amount"]
        )
        
        # Update payment status
        await db.db.payments.update_one(
            {"_id": ObjectId(payment_id)},
            {"$set": {
                "status": PaymentStatus.REFUNDED,
                "refundTransactionId": refund_result["id"],
                "refundReason": reason,
                "updatedAt": datetime.utcnow()
            }}
        )
        
        # Get the updated payment
        updated_payment = await get_payment_by_id(payment_id)
        
        # Create refund transaction
        transaction_data = {
            "userId": payment["clientId"],
            "type": TransactionType.REFUND,
            "amount": payment["amount"],
            "currency": payment["currency"],
            "status": PaymentStatus.COMPLETED,
            "description": f"Refund for booking #{payment['bookingId']}",
            "bookingId": payment["bookingId"],
            "paymentId": payment_id,
            "createdAt": datetime.utcnow()
        }
        
        await db.db.transactions.insert_one(transaction_data)
        
        # Update booking payment status
        await db.db.bookings.update_one(
            {"_id": ObjectId(payment["bookingId"])},
            {"$set": {"paymentStatus": PaymentStatus.REFUNDED}}
        )
        
        # Send notification to client
        notification = NotificationCreate(
            userId=payment["clientId"],
            type=NotificationType.PAYMENT_RECEIVED,
            title="Payment Refunded",
            message=f"Your payment of {payment['currency']} {payment['amount']} for booking #{payment['bookingId']} has been refunded",
            data={"bookingId": payment["bookingId"]}
        )
        
        await create_notification(notification)
        
        return updated_payment
        
    except Exception as e:
        logger.error(f"Error processing refund: {str(e)}")
        return None

async def get_payment_by_id(payment_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a payment by ID
    """
    try:
        payment = await db.db.payments.find_one({"_id": ObjectId(payment_id)})
        if payment:
            payment["id"] = str(payment["_id"])
        return payment
    except:
        return None

async def get_booking_payment(booking_id: str) -> Optional[Dict[str, Any]]:
    """
    Get payment for a booking
    """
    payment = await db.db.payments.find_one({"bookingId": booking_id})
    if payment:
        payment["id"] = str(payment["_id"])
    return payment

async def get_client_payments(
    client_id: str,
    skip: int = 0,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Get payments made by a client
    """
    cursor = db.db.payments.find({"clientId": client_id}).skip(skip).limit(limit).sort("createdAt", -1)
    payments = await cursor.to_list(length=limit)
    
    # Transform _id field to string
    for payment in payments:
        payment["id"] = str(payment["_id"])
    
    return payments

async def get_stylist_payments(
    stylist_id: str,
    skip: int = 0,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Get payments received by a stylist
    """
    cursor = db.db.payments.find({"stylistId": stylist_id}).skip(skip).limit(limit).sort("createdAt", -1)
    payments = await cursor.to_list(length=limit)
    
    # Transform _id field to string
    for payment in payments:
        payment["id"] = str(payment["_id"])
    
    return payments

async def add_payment_method(payment_method_in: PaymentMethodCreate) -> Dict[str, Any]:
    """
    Add a payment method for a user
    """
    # Create payment method data
    payment_method_data = payment_method_in.dict()
    payment_method_data["createdAt"] = datetime.utcnow()
    
    # Process based on payment method type
    if payment_method_in.type in [PaymentMethod.CREDIT_CARD, PaymentMethod.DEBIT_CARD]:
        # Store only last 4 digits of card number
        if payment_method_in.cardNumber:
            payment_method_data["lastFour"] = payment_method_in.cardNumber[-4:]
            payment_method_data["cardBrand"] = detect_card_brand(payment_method_in.cardNumber)
            
            # Remove sensitive data
            payment_method_data.pop("cardNumber", None)
    
    elif payment_method_in.type == PaymentMethod.NETBANKING:
        # Store only last 4 digits of bank account
        if payment_method_in.bankAccountNumber:
            payment_method_data["bankAccountLast4"] = payment_method_in.bankAccountNumber[-4:]
            
            # Remove sensitive data
            payment_method_data.pop("bankAccountNumber", None)
    
    # If this is default payment method, reset other default methods
    if payment_method_data.get("isDefault", False):
        await db.db.payment_methods.update_many(
            {"userId": payment_method_in.userId},
            {"$set": {"isDefault": False}}
        )
    
    # Insert payment method into database
    result = await db.db.payment_methods.insert_one(payment_method_data)
    
    # Get the created payment method
    created_method = await db.db.payment_methods.find_one({"_id": result.inserted_id})
    
    # Transform the _id field to string
    created_method["id"] = str(created_method["_id"])
    
    return created_method

async def get_payment_methods(user_id: str) -> List[Dict[str, Any]]:
    """
    Get payment methods for a user
    """
    cursor = db.db.payment_methods.find({"userId": user_id})
    methods = await cursor.to_list(length=100)
    
    # Transform _id field to string
    for method in methods:
        method["id"] = str(method["_id"])
    
    return methods

async def delete_payment_method(method_id: str, user_id: str) -> bool:
    """
    Delete a payment method
    """
    result = await db.db.payment_methods.delete_one(
        {"_id": ObjectId(method_id), "userId": user_id}
    )
    
    return result.deleted_count > 0

async def set_default_payment_method(method_id: str, user_id: str) -> bool:
    """
    Set a payment method as default
    """
    # Reset all payment methods for user
    await db.db.payment_methods.update_many(
        {"userId": user_id},
        {"$set": {"isDefault": False}}
    )
    
    # Set the selected method as default
    result = await db.db.payment_methods.update_one(
        {"_id": ObjectId(method_id), "userId": user_id},
        {"$set": {"isDefault": True}}
    )
    
    return result.modified_count > 0

async def create_payout(payout_in: PayoutCreate) -> Dict[str, Any]:
    """
    Create a payout for a stylist
    """
    # Get bank account
    bank_account = await db.db.payment_methods.find_one({"_id": ObjectId(payout_in.bankAccountId)})
    if not bank_account:
        return None
    
    # Create payout data
    payout_data = payout_in.dict()
    payout_data["status"] = PaymentStatus.PENDING
    payout_data["createdAt"] = datetime.utcnow()
    
    try:
        # Process payout with payment gateway
        payout_result = await payment_gateway.create_payout(
            bank_account,
            payout_in.amount,
            payout_in.currency,
            description=payout_in.description
        )
        
        # Update payout with transaction ID
        payout_data["transactionId"] = payout_result["id"]
        
        # Insert payout into database
        result = await db.db.payouts.insert_one(payout_data)
        
        # Get the created payout
        created_payout = await db.db.payouts.find_one({"_id": result.inserted_id})
        
        # Transform the _id field to string
        created_payout["id"] = str(created_payout["_id"])
        
        # Create transaction record
        transaction_data = {
            "userId": payout_in.stylistId,
            "type": TransactionType.PAYOUT,
            "amount": payout_in.amount,
            "currency": payout_in.currency,
            "status": PaymentStatus.PENDING,
            "description": payout_in.description or f"Payout to bank account",
            "payoutId": str(result.inserted_id),
            "createdAt": datetime.utcnow()
        }
        
        await db.db.transactions.insert_one(transaction_data)
        
        return created_payout
        
    except Exception as e:
        logger.error(f"Error processing payout: {str(e)}")
        return None

async def get_stylist_payouts(
    stylist_id: str,
    skip: int = 0,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Get payouts for a stylist
    """
    cursor = db.db.payouts.find({"stylistId": stylist_id}).skip(skip).limit(limit).sort("createdAt", -1)
    payouts = await cursor.to_list(length=limit)
    
    # Transform _id field to string
    for payout in payouts:
        payout["id"] = str(payout["_id"])
    
    return payouts

async def get_user_transactions(
    user_id: str,
    skip: int = 0,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Get transactions for a user
    """
    cursor = db.db.transactions.find({"userId": user_id}).skip(skip).limit(limit).sort("createdAt", -1)
    transactions = await cursor.to_list(length=limit)
    
    # Transform _id field to string
    for transaction in transactions:
        transaction["id"] = str(transaction["_id"])
    
    return transactions

async def get_stylist_payment_statistics(stylist_id: str) -> Dict[str, Any]:
    """
    Get payment statistics for a stylist
    """
    # Get total earnings (completed payments)
    earnings_pipeline = [
        {"$match": {
            "stylistId": stylist_id,
            "status": PaymentStatus.COMPLETED
        }},
        {"$group": {
            "_id": None,
            "totalEarnings": {"$sum": "$stylistAmount"}
        }}
    ]
    
    earnings_result = await db.db.payments.aggregate(earnings_pipeline).to_list(length=1)
    total_earnings = earnings_result[0]["totalEarnings"] if earnings_result else 0
    
    # Get pending payouts
    pending_pipeline = [
        {"$match": {
            "stylistId": stylist_id,
            "status": PaymentStatus.PENDING
        }},
        {"$group": {
            "_id": None,
            "pendingPayouts": {"$sum": "$amount"}
        }}
    ]
    
    pending_result = await db.db.payouts.aggregate(pending_pipeline).to_list(length=1)
    pending_payouts = pending_result[0]["pendingPayouts"] if pending_result else 0
    
    # Get booking counts
    total_bookings = await db.db.bookings.count_documents({"stylistId": stylist_id})
    completed_bookings = await db.db.bookings.count_documents({
        "stylistId": stylist_id,
        "status": "completed"
    })
    
    return {
        "totalEarnings": total_earnings,
        "pendingPayouts": pending_payouts,
        "totalBookings": total_bookings,
        "completedBookings": completed_bookings
    }

def detect_card_brand(card_number: str) -> str:
    """
    Detect credit card brand from card number
    """
    if not card_number:
        return "Unknown"
        
    # Remove spaces and dashes
    card_number = card_number.replace(" ", "").replace("-", "")
    
    # Visa: Starts with 4
    if card_number.startswith("4"):
        return "Visa"
        
    # Mastercard: Starts with 51-55 or 2221-2720
    if card_number.startswith("5") and len(card_number) >= 2:
        if "51" <= card_number[:2] <= "55":
            return "Mastercard"
    
    if len(card_number) >= 4:
        if "2221" <= card_number[:4] <= "2720":
            return "Mastercard"
    
    # Amex: Starts with 34 or 37
    if len(card_number) >= 2:
        if card_number[:2] in ["34", "37"]:
            return "American Express"
    
    # Discover: Starts with 6011, 622126-622925, 644-649, or 65
    if card_number.startswith("6"):
        if len(card_number) >= 4 and card_number[:4] == "6011":
            return "Discover"
        if len(card_number) >= 6 and "622126" <= card_number[:6] <= "622925":
            return "Discover"
        if len(card_number) >= 3 and "644" <= card_number[:3] <= "649":
            return "Discover"
        if len(card_number) >= 2 and card_number[:2] == "65":
            return "Discover"
    
    return "Unknown"
