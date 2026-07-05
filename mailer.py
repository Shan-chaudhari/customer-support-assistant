"""
Sends a plain-text email to the clinic when a booking is made.

SETUP:
1. On the clinic's Gmail account, enable 2-Step Verification, then create
   an "App Password" (Google Account -> Security -> App passwords).
2. Set these environment variables (e.g. in a .env file, already loaded
   via python-dotenv in app.py):
     CLINIC_GMAIL_ADDRESS=clinic@gmail.com
     CLINIC_GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx
     CLINIC_NOTIFY_EMAIL=clinic@gmail.com   (where the notification is sent;
                                              can be the same address or different)
"""

import os
import smtplib
from email.message import EmailMessage

import config


def send_booking_notification(service_name, patient_name, phone, date_str, time_str):
    sender = os.environ["CLINIC_GMAIL_ADDRESS"]
    app_password = os.environ["CLINIC_GMAIL_APP_PASSWORD"]
    recipient = os.environ.get("CLINIC_NOTIFY_EMAIL", sender)

    msg = EmailMessage()
    msg["Subject"] = f"New appointment request: {patient_name} ({date_str} {time_str})"
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(
        f"New appointment request via chatbot\n\n"
        f"Name: {patient_name}\n"
        f"Phone: {phone}\n"
        f"Service: {service_name}\n"
        f"Date: {date_str}\n"
        f"Time: {time_str}\n"
    )

    with smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT) as smtp:
        smtp.login(sender, app_password)
        smtp.send_message(msg)
        