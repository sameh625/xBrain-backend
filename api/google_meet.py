"""Google Calendar API integration for auto-generating Google Meet links.

The backend uses a single 'host' Google account (the xBrain Gmail) to create
calendar events that include a Meet conference. Both meeting participants are
added as attendees so they receive calendar invites.

Credentials are obtained via the one-time OAuth flow in
scripts/get_google_refresh_token.py and stored as four env vars:
  GOOGLE_CLIENT_ID
  GOOGLE_CLIENT_SECRET
  GOOGLE_REFRESH_TOKEN
  GOOGLE_CALENDAR_ID    (usually 'primary')
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)


def _build_calendar_service():
    """Build an authenticated Google Calendar API client.

    Imports are inside the function so the rest of the codebase doesn't fail
    to load when google-api-python-client isn't installed (e.g., before
    `pip install`).
    """
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    if not (settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET and settings.GOOGLE_REFRESH_TOKEN):
        raise GoogleMeetError(
            "Google credentials not configured. Set GOOGLE_CLIENT_ID, "
            "GOOGLE_CLIENT_SECRET, and GOOGLE_REFRESH_TOKEN env vars."
        )

    creds = Credentials(
        token=None,                                      # access token; will be refreshed on first call
        refresh_token=settings.GOOGLE_REFRESH_TOKEN,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=['https://www.googleapis.com/auth/calendar.events'],
    )
    return build('calendar', 'v3', credentials=creds, cache_discovery=False)


class GoogleMeetError(Exception):
    """Raised when creating a Google Meet event fails."""


def create_meet_event(
    *,
    summary: str,
    description: str,
    starts_at: datetime,
    duration_minutes: int,
    attendee_emails: list[str],
) -> tuple[str, str]:
    """Create a Google Calendar event with an auto-generated Meet link.

    Args:
        summary: Event title shown in the calendar.
        description: Longer body text shown in the calendar event.
        starts_at: Timezone-aware start time.
        duration_minutes: Length of the meeting.
        attendee_emails: List of email addresses to invite.

    Returns:
        A (meet_url, event_id) tuple. `meet_url` is the auto-generated
        https://meet.google.com/... link; `event_id` is the Google Calendar
        event ID (saved so we can update / delete the event later).

    Raises:
        GoogleMeetError if Google rejects the request or no Meet link is returned.
    """
    if starts_at.tzinfo is None:
        raise GoogleMeetError("starts_at must be timezone-aware")

    ends_at = starts_at + timedelta(minutes=duration_minutes)

    event_body = {
        'summary': summary,
        'description': description,
        'start': {'dateTime': starts_at.isoformat(), 'timeZone': 'UTC'},
        'end':   {'dateTime': ends_at.isoformat(),   'timeZone': 'UTC'},
        'attendees': [{'email': email} for email in attendee_emails],
        'guestsCanModify': False,
        'guestsCanSeeOtherGuests': True,
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email',   'minutes': 60},
                {'method': 'popup',   'minutes': 15},
            ],
        },
        'conferenceData': {
            'createRequest': {
                'requestId': str(uuid.uuid4()),                    # idempotency key
                'conferenceSolutionKey': {'type': 'hangoutsMeet'},
            },
        },
    }

    try:
        service = _build_calendar_service()
        created = service.events().insert(
            calendarId=settings.GOOGLE_CALENDAR_ID,
            body=event_body,
            conferenceDataVersion=1,        # required for Meet link generation
            sendUpdates='all',              # email all attendees
        ).execute()
    except Exception as e:
        logger.exception("Google Calendar API failed to create event")
        raise GoogleMeetError(f"Failed to create Google Meet event: {e}") from e

    meet_link = created.get('hangoutLink')
    if not meet_link:
        # The conferenceData field may have a more detailed structure on rare occasions.
        conference_data = created.get('conferenceData', {})
        for entry in conference_data.get('entryPoints', []):
            if entry.get('entryPointType') == 'video' and entry.get('uri'):
                meet_link = entry['uri']
                break

    if not meet_link:
        raise GoogleMeetError(
            "Google created the event but did not return a Meet link. "
            "This usually means the host account is not allowed to create Meet conferences."
        )

    event_id = created.get('id', '')
    return meet_link, event_id


def cancel_meet_event(event_id: str) -> None:
    """Cancel/delete a previously created Google Calendar event.

    Silently logs and continues on failure — cancellation cleanup should
    never block the user-facing flow.
    """
    if not event_id:
        return
    try:
        service = _build_calendar_service()
        service.events().delete(
            calendarId=settings.GOOGLE_CALENDAR_ID,
            eventId=event_id,
            sendUpdates='all',
        ).execute()
    except Exception:
        logger.exception("Failed to cancel Google Calendar event %s", event_id)
