import base64
from typing import Optional, Dict, Any
import httpx
from datetime import datetime

from app.core.config import settings

ZOOM_OAUTH_TOKEN_URL = "https://zoom.us/oauth/token"
ZOOM_CREATE_MEETING_URL_TMPL = "https://api.zoom.us/v2/users/{userId}/meetings"


async def _get_access_token() -> Optional[str]:
    """
    Obtain Zoom Server-to-Server OAuth access token.
    Returns None if credentials are missing or request fails.
    """
    account_id = settings.ZOOM_ACCOUNT_ID
    client_id = settings.ZOOM_CLIENT_ID
    client_secret = settings.ZOOM_CLIENT_SECRET

    if not account_id or not client_id or not client_secret:
        return None

    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    params = {
        "grant_type": "account_credentials",
        "account_id": account_id,
    }

    headers = {
        "Authorization": f"Basic {basic}",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(ZOOM_OAUTH_TOKEN_URL, params=params, headers=headers)
        if resp.status_code != 200:
            return None
        data = resp.json()
        return data.get("access_token")


async def create_zoom_meeting(
    topic: str,
    start_time_iso: str,
    duration_minutes: int,
    timezone: str = "UTC",
) -> Optional[Dict[str, Any]]:
    """
    Create a Zoom meeting. Returns Zoom API response (dict) or None on failure.
    - start_time_iso: ISO8601 e.g. "2025-01-01T10:00:00Z"
    """
    token = await _get_access_token()
    if not token:
        return None

    payload = {
        "topic": topic,
        "type": 2,  # scheduled meeting
        "start_time": start_time_iso,
        "duration": duration_minutes,
        "timezone": timezone,
        "settings": {
            "join_before_host": False,
            "waiting_room": True,
            "approval_type": 2,  # no registration
        },
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    user_id = settings.ZOOM_USER_ID or "me"
    url = ZOOM_CREATE_MEETING_URL_TMPL.format(userId=user_id)

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code not in (200, 201):
            # Log full error body for diagnostics
            try:
                print(f"Zoom create meeting failed {resp.status_code}: {resp.text}")
            except Exception:
                pass
            return None
        try:
            return resp.json()
        except Exception:
            return None
