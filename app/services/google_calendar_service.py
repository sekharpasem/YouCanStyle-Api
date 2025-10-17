import base64
import json
import random
import string
from datetime import datetime
from typing import Optional, Dict, Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.config import settings

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
]


def _load_service_account_credentials():
    """Load Google service account credentials from env (base64 JSON or path)."""
    info = None
    if settings.GOOGLE_SA_JSON_BASE64:
        try:
            decoded = base64.b64decode(settings.GOOGLE_SA_JSON_BASE64)
            info = json.loads(decoded)
        except Exception as e:
            print(f"Failed to decode GOOGLE_SA_JSON_BASE64: {e}")
    elif settings.GOOGLE_SA_JSON_PATH:
        try:
            with open(settings.GOOGLE_SA_JSON_PATH, "r", encoding="utf-8") as f:
                info = json.load(f)
        except Exception as e:
            print(f"Failed to read GOOGLE_SA_JSON_PATH: {e}")

    if not info:
        return None

    try:
        creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        # Use domain-wide delegation to impersonate a user (required for Meet)
        impersonate = settings.GOOGLE_CALENDAR_IMPERSONATE
        if impersonate:
            creds = creds.with_subject(impersonate)
        return creds
    except Exception as e:
        print(f"Failed to build service account credentials: {e}")
        return None


def _random_request_id(length: int = 12) -> str:
    return "req-" + "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def _extract_meet_link(event: Dict[str, Any]) -> Optional[str]:
    # Prefer conferenceData.entryPoints video uri
    try:
        eps = event.get("conferenceData", {}).get("entryPoints", [])
        for ep in eps:
            if ep.get("entryPointType") == "video" and isinstance(ep.get("uri"), str):
                return ep["uri"]
    except Exception:
        pass
    # Fallback to hangoutLink
    link = event.get("hangoutLink")
    if isinstance(link, str) and link:
        return link
    return None


async def create_google_meet_event(
    summary: str,
    start_dt: datetime,
    end_dt: datetime,
    timezone: str = "UTC",
) -> Optional[str]:
    """
    Create a Google Calendar event with Google Meet conference and return the Meet link (uri).
    Requires a Workspace account with domain-wide delegation enabled.
    """
    creds = _load_service_account_credentials()
    if not creds:
        print("Google Calendar credentials not configured; skipping Meet creation")
        return None

    event_body = {
        "summary": summary,
        "start": {
            "dateTime": start_dt.isoformat(),
            "timeZone": timezone,
        },
        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": timezone,
        },
        "conferenceData": {
            "createRequest": {
                "requestId": _random_request_id(),
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
    }

    try:
        service = build("calendar", "v3", credentials=creds)
        event = (
            service.events()
            .insert(
                calendarId="primary",
                body=event_body,
                conferenceDataVersion=1,
                sendNotifications=False,
            )
            .execute()
        )
        return _extract_meet_link(event)
    except HttpError as e:
        try:
            print(f"Google Calendar create event error {e.status_code}: {e.error_details if hasattr(e, 'error_details') else e}")
        except Exception:
            print(f"Google Calendar create event error: {e}")
        return None
    except Exception as e:
        print(f"Google Calendar create event unexpected error: {e}")
        return None
