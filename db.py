
import sqlite3
import datetime
from contextlib import contextmanager

import config


def _generate_all_slots():
    """All possible time-of-day slots within business hours, as 'HH:MM' strings."""
    slots = []
    current = datetime.datetime.combine(datetime.date.today(), config.BUSINESS_HOURS_START)
    end = datetime.datetime.combine(datetime.date.today(), config.BUSINESS_HOURS_END)
    step = datetime.timedelta(minutes=config.SLOT_MINUTES)
    while current < end:
        slots.append(current.strftime("%H:%M"))
        current += step
    return slots


ALL_SLOTS = _generate_all_slots()


@contextmanager
def get_connection():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service TEXT NOT NULL,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                date TEXT NOT NULL,          -- 'YYYY-MM-DD'
                time TEXT NOT NULL,          -- 'HH:MM'
                calendar_event_id TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(date, time)
            )
            """
        )


def get_upcoming_business_days(count=None):
    """Returns the next `count` business days (per config.WORKING_DAYS) as
    a list of (label, value) tuples, e.g. ('Mon, Jul 6', '2026-07-06')."""
    count = count or config.DAYS_AHEAD_TO_OFFER
    days = []
    cursor = datetime.date.today()
    while len(days) < count:
        cursor += datetime.timedelta(days=1)
        if cursor.weekday() in config.WORKING_DAYS:
            label = cursor.strftime("%a, %b %-d")
            value = cursor.isoformat()
            days.append((label, value))
    return days


def get_booked_times_for_date(date_str):
    """Times already taken in our own DB for a given date."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT time FROM bookings WHERE date = ?", (date_str,)
        ).fetchall()
    return {row["time"] for row in rows}


def get_available_slots(date_str, externally_busy_times=None):
    """
    Available 'HH:MM' slots for a date, excluding:
    - slots already booked in our DB
    - slots reported busy by an external source (e.g. Google Calendar),
      passed in as `externally_busy_times`
    """
    booked = get_booked_times_for_date(date_str)
    busy = set(externally_busy_times or [])
    return [slot for slot in ALL_SLOTS if slot not in booked and slot not in busy]


class SlotUnavailableError(Exception):
    """Raised when a slot was taken between being offered and being booked."""


def create_booking(service, name, phone, date_str, time_str):
    """
    Inserts a booking. Relies on the UNIQUE(date, time) constraint to be
    the final word on conflicts, closing the race-condition window between
    checking availability and committing the booking.
    """
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO bookings (service, name, phone, date, time, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (service, name, phone, date_str, time_str, datetime.datetime.utcnow().isoformat()),
            )
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        raise SlotUnavailableError(f"{date_str} {time_str} was just booked by someone else.")


def attach_calendar_event_id(booking_id, event_id):
    with get_connection() as conn:
        conn.execute(
            "UPDATE bookings SET calendar_event_id = ? WHERE id = ?",
            (event_id, booking_id),
        )