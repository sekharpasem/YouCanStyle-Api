from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import get_current_user
from app.db.mongodb import db
from app.schemas.payout import PayoutCreate, PayoutResponse, PayoutSummaryResponse, PayoutStatus
from app.services.stylist_service import get_stylist_by_user_id, get_stylist_by_id

router = APIRouter()


def _as_response(doc) -> PayoutResponse:
    return PayoutResponse(
        id=str(doc.get("_id")),
        stylistName=doc.get("stylistName", ""),
        stylistId=str(doc.get("stylistId", "")),
        bookingId=str(doc.get("bookingId", "")),
        amount=float(doc.get("amount", 0.0)),
        commission=float(doc.get("commission", 0.0)),
        status=PayoutStatus(doc.get("status", PayoutStatus.pending)),
        createdAt=doc.get("createdAt", datetime.utcnow()),
    )


@router.post("/", response_model=PayoutResponse, status_code=status.HTTP_201_CREATED)
async def create_payout(payout_in: PayoutCreate, current_user: dict = Depends(get_current_user)):
    """
    Create a payout record. Accessible by admin or the same stylist only.
    Commission is 20% on amount.
    """
    # If caller is not admin, ensure they are the stylist referenced
    if current_user.get("role") != "admin":
        stylist = await get_stylist_by_user_id(str(current_user.get("_id")))
        if not stylist:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stylist profile not found")
        if str(payout_in.stylistId) != str(stylist.get("_id")):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to create payout for another stylist")

    # Optional: validate stylist exists
    stylist_doc = await get_stylist_by_id(payout_in.stylistId)
    if not stylist_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stylist not found")

    commission = round(payout_in.amount * 0.20, 2)
    doc = {
        "stylistName": payout_in.stylistName,
        "stylistId": str(payout_in.stylistId),
        "bookingId": str(payout_in.bookingId),
        "amount": float(payout_in.amount),
        "commission": float(commission),
        "status": payout_in.status.value if isinstance(payout_in.status, PayoutStatus) else str(payout_in.status).lower(),
        "createdAt": datetime.utcnow(),
    }

    res = await db.db.stylists_payouts.insert_one(doc)
    saved = await db.db.stylists_payouts.find_one({"_id": res.inserted_id})
    return _as_response(saved)


@router.get("/summary", response_model=PayoutSummaryResponse)
async def get_my_payout_summary(current_user: dict = Depends(get_current_user)):
    """
    Return stylist earnings summary for the current stylist:
    - weeklyEarnings: sum of success payouts in current week (Mon..today)
    - monthlyEarnings: sum of success payouts in current month
    - pendingPayouts: sum of pending payouts (all time)
    """
    stylist = await get_stylist_by_user_id(str(current_user.get("_id")))
    if not stylist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stylist profile not found")

    stylist_id = str(stylist.get("_id"))
    now = datetime.utcnow()
    # Week starts Monday
    start_of_week = now - timedelta(days=(now.weekday()))
    start_of_week = datetime(start_of_week.year, start_of_week.month, start_of_week.day)
    start_of_month = datetime(now.year, now.month, 1)

    # Weekly earnings (status success)
    weekly_cursor = db.db.stylists_payouts.find({
        "stylistId": stylist_id,
        "status": PayoutStatus.success.value,
        "createdAt": {"$gte": start_of_week}
    })
    weekly = 0.0
    async for d in weekly_cursor:
        weekly += float(d.get("amount", 0.0))

    # Monthly earnings (status success)
    monthly_cursor = db.db.stylists_payouts.find({
        "stylistId": stylist_id,
        "status": PayoutStatus.success.value,
        "createdAt": {"$gte": start_of_month}
    })
    monthly = 0.0
    async for d in monthly_cursor:
        monthly += float(d.get("amount", 0.0))

    # Pending payouts (status pending)
    pending_cursor = db.db.stylists_payouts.find({
        "stylistId": stylist_id,
        "status": PayoutStatus.pending.value,
    })
    pending = 0.0
    async for d in pending_cursor:
        pending += float(d.get("amount", 0.0))

    return PayoutSummaryResponse(
        weeklyEarnings=round(weekly, 2),
        monthlyEarnings=round(monthly, 2),
        pendingPayouts=round(pending, 2),
    )


@router.get("/me", response_model=List[PayoutResponse])
async def list_my_payouts(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    """
    Return all payout records for the current stylist (paginated).
    """
    stylist = await get_stylist_by_user_id(str(current_user.get("_id")))
    if not stylist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stylist profile not found")

    stylist_id = str(stylist.get("_id"))
    cursor = db.db.stylists_payouts.find({"stylistId": stylist_id}).skip(skip).limit(limit).sort("createdAt", -1)

    results: List[PayoutResponse] = []
    async for d in cursor:
        results.append(_as_response(d))
    return results
