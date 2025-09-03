from fastapi import APIRouter
from app.api.api_v1.endpoints import stylists, bookings, auth, chat, payments, notifications, uploads, services, availability, stylist_auth

router = APIRouter()

# Include all routers
router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(stylist_auth.router, prefix="/stylist-auth", tags=["Stylist Authentication"])
router.include_router(stylists.router, prefix="/stylists", tags=["Stylists"])
router.include_router(bookings.router, prefix="/bookings", tags=["Bookings"])
router.include_router(chat.router, prefix="/chat", tags=["Chat"])
router.include_router(payments.router, prefix="/payments", tags=["Payments"])
router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
router.include_router(uploads.router, prefix="/uploads", tags=["Uploads"])
router.include_router(services.router, prefix="/services", tags=["Services"])
router.include_router(availability.router, prefix="/availability", tags=["Availability"])
