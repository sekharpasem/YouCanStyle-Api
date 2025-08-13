import pytest
import asyncio
from httpx import AsyncClient
from datetime import datetime, timedelta
import json
import os
from bson.objectid import ObjectId

# Import our FastAPI app
from app.main import app
from app.db.mongodb import db
from app.core.config import settings

# Test data
test_user = {
    "email": "testuser@youcanstyle.com",
    "password": "TestPassword123",
    "fullName": "Test User",
    "phoneNumber": "+919999999999"
}

test_stylist_user = {
    "email": "teststylist@youcanstyle.com",
    "password": "TestPassword123",
    "fullName": "Test Stylist",
    "phoneNumber": "+919888888888"
}

test_stylist = {
    "yearsOfExperience": 5,
    "bio": "Professional stylist with 5 years of experience",
    "services": ["Hair Styling", "Makeup", "Fashion Consultation"],
    "hourlyRate": 1000
}

test_booking = {
    "date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
    "startTime": "10:00 AM",
    "endTime": "11:00 AM",
    "services": ["Hair Styling"],
    "totalAmount": 1000,
    "isOnlineSession": False,
    "location": {
        "address": "Test Location",
        "latitude": 12.9716,
        "longitude": 77.5946
    },
    "notes": "Test booking for payment flow"
}

test_payment = {
    "amount": 1000,
    "currency": "INR",
    "paymentMethod": "credit_card"
}

test_payment_method = {
    "type": "credit_card",
    "cardNumber": "4111111111111111",
    "cardExpiry": "12/25",
    "cardHolderName": "Test User",
    "isDefault": True
}

test_payout = {
    "amount": 900,  # 90% of payment amount (10% platform fee)
    "currency": "INR",
    "description": "Test payout"
}

@pytest.mark.asyncio
async def test_payment_flow():
    """
    Test the complete payment flow:
    1. Register a client and stylist
    2. Create stylist profile
    3. Create a booking
    4. Add payment method
    5. Make payment for booking
    6. Check transaction history
    7. Create payout request
    8. Refund payment
    """
    # Create test client
    async with AsyncClient(app=app, base_url="http://test") as client:
        print("1. Registering test users...")
        
        # Register client user
        response = await client.post("/api/v1/auth/register", json=test_user)
        assert response.status_code == 200
        client_data = response.json()
        client_id = client_data["user"]["_id"]
        client_token = client_data["token"]
        
        # Register stylist user
        response = await client.post("/api/v1/auth/register", json=test_stylist_user)
        assert response.status_code == 200
        stylist_user_data = response.json()
        stylist_user_id = stylist_user_data["user"]["_id"]
        stylist_token = stylist_user_data["token"]
        
        print("2. Creating stylist profile...")
        
        # Create stylist profile
        response = await client.post(
            "/api/v1/stylists", 
            json=test_stylist,
            headers={"Authorization": f"Bearer {stylist_token}"}
        )
        assert response.status_code == 200
        stylist_data = response.json()
        stylist_id = stylist_data["id"]
        
        print("3. Creating booking...")
        
        # Create booking
        booking_data = test_booking.copy()
        booking_data["stylistId"] = stylist_id
        
        response = await client.post(
            "/api/v1/bookings", 
            json=booking_data,
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert response.status_code == 200
        booking = response.json()
        booking_id = booking["id"]
        
        print("4. Adding payment method...")
        
        # Add payment method
        payment_method_data = test_payment_method.copy()
        payment_method_data["userId"] = client_id
        
        response = await client.post(
            "/api/v1/payments/methods", 
            json=payment_method_data,
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert response.status_code == 200
        payment_method = response.json()
        
        # Check payment methods
        response = await client.get(
            "/api/v1/payments/methods",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert response.status_code == 200
        payment_methods = response.json()
        assert len(payment_methods) > 0
        
        print("5. Making payment for booking...")
        
        # Make payment
        payment_data = test_payment.copy()
        payment_data["bookingId"] = booking_id
        
        response = await client.post(
            "/api/v1/payments", 
            json=payment_data,
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert response.status_code == 200
        payment = response.json()
        payment_id = payment["id"]
        
        # Get payment for booking
        response = await client.get(
            f"/api/v1/payments/booking/{booking_id}",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert response.status_code == 200
        booking_payment = response.json()
        assert booking_payment["id"] == payment_id
        
        print("6. Checking transaction history...")
        
        # Check client transactions
        response = await client.get(
            "/api/v1/payments/transactions",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert response.status_code == 200
        transactions = response.json()
        assert len(transactions) > 0
        
        # Check stylist payments
        response = await client.get(
            "/api/v1/payments/stylist/me",
            headers={"Authorization": f"Bearer {stylist_token}"}
        )
        assert response.status_code == 200
        stylist_payments = response.json()
        assert len(stylist_payments) > 0
        
        # Check payment statistics
        response = await client.get(
            "/api/v1/payments/statistics",
            headers={"Authorization": f"Bearer {stylist_token}"}
        )
        assert response.status_code == 200
        statistics = response.json()
        assert statistics["totalEarnings"] > 0
        
        print("7. Creating payout request...")
        
        # Create bank account for stylist
        bank_account = {
            "userId": stylist_user_id,
            "type": "netbanking",
            "bankName": "Test Bank",
            "bankAccountNumber": "1234567890",
            "ifscCode": "TEST0001234",
            "isDefault": True
        }
        
        response = await client.post(
            "/api/v1/payments/methods", 
            json=bank_account,
            headers={"Authorization": f"Bearer {stylist_token}"}
        )
        assert response.status_code == 200
        bank_account_data = response.json()
        bank_account_id = bank_account_data["id"]
        
        # Request payout
        payout_data = test_payout.copy()
        payout_data["stylistId"] = stylist_id
        payout_data["bankAccountId"] = bank_account_id
        
        response = await client.post(
            "/api/v1/payments/payouts", 
            json=payout_data,
            headers={"Authorization": f"Bearer {stylist_token}"}
        )
        assert response.status_code == 200
        payout = response.json()
        
        # Check stylist payouts
        response = await client.get(
            "/api/v1/payments/payouts/stylist/me",
            headers={"Authorization": f"Bearer {stylist_token}"}
        )
        assert response.status_code == 200
        payouts = response.json()
        assert len(payouts) > 0
        
        print("8. Refunding payment...")
        
        # Refund payment
        response = await client.post(
            f"/api/v1/payments/{payment_id}/refund", 
            json={"reason": "Test refund"},
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert response.status_code == 200
        refunded_payment = response.json()
        assert refunded_payment["status"] == "refunded"
        
        print("Payment flow test completed successfully!")

# Run test if executed directly
if __name__ == "__main__":
    asyncio.run(test_payment_flow())
