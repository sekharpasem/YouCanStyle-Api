import json
from typing import Any, Dict, List, Optional
from datetime import datetime

import httpx

from app.core.config import settings


def _format_date(dt: Any) -> str:
    try:
        if isinstance(dt, str):
            # attempt ISO parse
            try:
                return datetime.fromisoformat(dt.replace("Z", "")).strftime("%Y-%m-%d")
            except Exception:
                return dt[:10]
        if isinstance(dt, datetime):
            return dt.strftime("%Y-%m-%d")
    except Exception:
        pass
    return ""


def _join_platforms(pref: Optional[List[Any]]) -> str:
    if not pref:
        return "-"
    vals: List[str] = []
    for p in pref:
        if isinstance(p, str):
            vals.append(p)
        else:
            # Enum value
            v = getattr(p, "value", None)
            if isinstance(v, str):
                vals.append(v)
    # Beautify labels
    label_map = {
        "zoom": "Zoom",
        "google_meet": "Google Meet",
        "whatsapp": "WhatsApp",
    }
    return ", ".join(label_map.get(v, v) for v in vals)


def _build_body_parameters(booking: Dict[str, Any]) -> List[Dict[str, str]]:
    client_name = booking.get("clientName") or "Client"
    stylist_name = booking.get("stylistName") or "Stylist"
    date_str = _format_date(booking.get("date"))
    start = booking.get("startTime") or ""
    end = booking.get("endTime") or ""
    platforms = _join_platforms(booking.get("meeting_preference"))
    meeting_link = booking.get("meetingLink") or "-"

    return [
        {"type": "text", "text": str(client_name)},
        {"type": "text", "text": str(stylist_name)},
        {"type": "text", "text": str(date_str)},
        {"type": "text", "text": f"{start}-{end}".strip("-")},
        {"type": "text", "text": platforms},
        {"type": "text", "text": str(meeting_link)},
    ]


def send_template_message_sync(
    to_e164: str,
    template_name: str,
    body_parameters: List[Dict[str, str]],
    language: Optional[str] = None,
) -> bool:
    if not settings.WHATSAPP_ENABLED:
        return False
    if not settings.WHATSAPP_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
        return False

    url = f"https://graph.facebook.com/v20.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload: Dict[str, Any] = {
        "messaging_product": "whatsapp",
        "to": to_e164,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": (language or settings.WHATSAPP_DEFAULT_LANG)},
            "components": [
                {
                    "type": "body",
                    "parameters": body_parameters,
                }
            ],
        },
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code >= 200 and resp.status_code < 300:
                return True
            # Log minimal details; avoid raising
            print(
                f"WhatsApp send failed: status={resp.status_code} body={resp.text[:300]}"
            )
            return False
    except Exception as e:
        print(f"WhatsApp send exception: {e}")
        return False


def send_booking_confirmation_sync(to_e164: str, booking: Dict[str, Any], language: Optional[str] = None) -> bool:
    body_params = _build_body_parameters(booking)
    return send_template_message_sync(
        to_e164=to_e164,
        template_name="booking_confirmation_client",
        body_parameters=body_params,
        language=language,
    )
