"""
Shared configuration for the booking system.
Adjust these to match the clinic's real hours.
"""

import datetime

# Business hours (24h clock)
BUSINESS_HOURS_START = datetime.time(9, 0)
BUSINESS_HOURS_END = datetime.time(17, 0)

# Length of each appointment slot
SLOT_MINUTES = 30

# 0 = Monday ... 6 = Sunday
WORKING_DAYS = {0, 1, 2, 3, 4}  # Mon-Fri

# How many upcoming business days to offer as date-picker buttons
DAYS_AHEAD_TO_OFFER = 7

DB_PATH = "bookings.db"

# Google Calendar
GOOGLE_CALENDAR_ID = "primary"  # or the clinic's specific calendar ID
GOOGLE_CREDENTIALS_PATH = "credentials.json"  # OAuth client secrets
GOOGLE_TOKEN_PATH = "token.json"  # cached user token after first auth

# Email (SMTP via Gmail app password)
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465