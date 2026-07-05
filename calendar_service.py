import datetime
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import config

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_calendar_service():
    creds = None
    if os.path.exists(config.GOOGLE_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(config.GOOGLE_TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(config.GOOGLE_CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(config.GOOGLE_TOKEN_PATH, "w") as token_file:
            token_file.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def get_busy_times_for_date(date_str):
    service = get_calendar_service()

    day_start = datetime.datetime.fromisoformat(date_str + "T00:00:00")
    day_end = day_start + datetime.timedelta(days=1)

    body = {
        "timeMin": day_start.isoformat() + "Z",
        "timeMax": day_end.isoformat() + "Z",
        "items": [{"id": config.GOOGLE_CALENDAR_ID}],
    }
    result = service.freebusy().query(body=body).execute()
    busy_periods = result["calendars"][config.GOOGLE_CALENDAR_ID]["busy"]

    busy_slots = set()
    for period in busy_periods:
        start = datetime.datetime.fromisoformat(period["start"].replace("Z", "+00:00"))
        end = datetime.datetime.fromisoformat(period["end"].replace("Z", "+00:00"))

        cursor = start
        step = datetime.timedelta(minutes=config.SLOT_MINUTES)
        while cursor < end:
            busy_slots.add(cursor.strftime("%H:%M"))
            cursor += step

    return busy_slots


def create_calendar_event(service_name, patient_name, phone, date_str, time_str):
    service = get_calendar_service()

    start_dt = datetime.datetime.fromisoformat(f"{date_str}T{time_str}:00")
    end_dt = start_dt + datetime.timedelta(minutes=config.SLOT_MINUTES)

    event = {
        "summary": f"{service_name} - {patient_name}",
        "description": f"Booked via chatbot.\nPhone: {phone}",
        "start": {"dateTime": start_dt.isoformat(), "timeZone": "America/Toronto"},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": "America/Toronto"},
    }

    created = service.events().insert(calendarId=config.GOOGLE_CALENDAR_ID, body=event).execute()
    return created["id"]
