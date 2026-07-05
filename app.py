import os
import logging

from flask import Flask, render_template, request, jsonify, session
from openai import OpenAI
from dotenv import load_dotenv

import config
import db
import calendar_service
import mailer

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]  # must be set in the environment

client = OpenAI()

logger = logging.getLogger(__name__)

db.init_db()

_KNOWLEDGE_CACHE = None


def get_knowledge_text():
    global _KNOWLEDGE_CACHE
    if _KNOWLEDGE_CACHE is None:
        with open("knowledge.txt", "r") as f:
            _KNOWLEDGE_CACHE = f.read()
    return _KNOWLEDGE_CACHE


def service_buttons():
    return [
        {"text": "Cleaning", "value": "Cleaning"},
        {"text": "Filling", "value": "Filling"},
        {"text": "Crown", "value": "Crown"},
        {"text": "Root Canal", "value": "Root Canal"},
    ]


def date_buttons():
    return [{"text": label, "value": value} for label, value in db.get_upcoming_business_days()]


def time_buttons(date_str):
    try:
        busy = calendar_service.get_busy_times_for_date(date_str)
    except Exception:
        logger.exception("Google Calendar lookup failed; falling back to DB-only availability")
        busy = set()

    slots = db.get_available_slots(date_str, externally_busy_times=busy)
    return [{"text": s, "value": s} for s in slots]


def new_booking_state():
    return {
        "active": False,
        "step": None,
        "service": None,
        "name": None,
        "phone": None,
        "date": None,
        "time": None,
    }


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"response": "Please send a message."}), 400

    user_wants_to_book = any(
        keyword in message.lower() for keyword in ["book", "appointment", "reserve", "schedule"]
    )

    if "booking" not in session:
        session["booking"] = new_booking_state()

    if user_wants_to_book:
        session["booking"] = new_booking_state()
        session["booking"]["active"] = True
        session["booking"]["step"] = "service"
        session.modified = True

        return jsonify({
            "response": "Sure! What type of appointment would you like?",
            "buttons": service_buttons(),
        })

    if session["booking"]["active"]:
        booking = session["booking"]
        step = booking["step"]

        if step == "service":
            booking["service"] = message
            booking["step"] = "name"
            session.modified = True
            return jsonify({"response": "Great! Could I have your full name, please?"})

        elif step == "name":
            booking["name"] = message
            booking["step"] = "phone"
            session.modified = True
            return jsonify({"response": "Thanks! What's the best phone number to reach you?"})

        elif step == "phone":
            booking["phone"] = message
            booking["step"] = "date"
            session.modified = True
            return jsonify({
                "response": "Perfect! What date would you like to book?",
                "buttons": date_buttons(),
            })

        elif step == "date":
            booking["date"] = message
            booking["step"] = "time"
            session.modified = True

            slots = time_buttons(message)
            if not slots:
                booking["step"] = "date"
                session.modified = True
                return jsonify({
                    "response": "Sorry, that day is fully booked. Please choose another date.",
                    "buttons": date_buttons(),
                })

            return jsonify({
                "response": "Great! What time works best for you?",
                "buttons": slots,
            })

        elif step == "time":
            chosen_time = message

            try:
                booking_id = db.create_booking(
                    service=booking["service"],
                    name=booking["name"],
                    phone=booking["phone"],
                    date_str=booking["date"],
                    time_str=chosen_time,
                )
            except db.SlotUnavailableError:
                fresh_slots = time_buttons(booking["date"])
                return jsonify({
                    "response": "Sorry, that time was just booked by someone else. Please pick another:",
                    "buttons": fresh_slots,
                })

            booking["time"] = chosen_time

            try:
                event_id = calendar_service.create_calendar_event(
                    booking["service"], booking["name"], booking["phone"],
                    booking["date"], booking["time"],
                )
                db.attach_calendar_event_id(booking_id, event_id)
            except Exception:
                logger.exception("Failed to create Google Calendar event for booking %s", booking_id)

            try:
                mailer.send_booking_notification(
                    booking["service"], booking["name"], booking["phone"],
                    booking["date"], booking["time"],
                )
            except Exception:
                logger.exception("Failed to send booking notification email for booking %s", booking_id)

            summary = (
                "Appointment Request\n\n"
                f"Name: {booking['name']}\n"
                f"Phone: {booking['phone']}\n"
                f"Service: {booking['service']}\n"
                f"Date: {booking['date']}\n"
                f"Time: {booking['time']}\n\n"
                "Your appointment has been booked. The clinic will contact you "
                "if anything needs to change."
            )

            session["booking"] = new_booking_state()
            session.modified = True

            return jsonify({"response": summary})

        else:
            session["booking"] = new_booking_state()
            session.modified = True
            return jsonify({"response": "Sorry, I didn't understand that. Let's try booking again."})

    if "conversation" not in session:
        session["conversation"] = []
    session["conversation"].append({"role": "user", "content": message})
    session.modified = True

    try:
        knowledge = get_knowledge_text()
    except OSError:
        logger.exception("Failed to read knowledge.txt")
        return jsonify({"response": "Sorry, something went wrong on our end. Please try again shortly."}), 500

    try:
        completion = client.responses.create(
            model="gpt-5.5",
            instructions=knowledge,
            input=session["conversation"],
        )
    except Exception:
        logger.exception("OpenAI request failed")
        return jsonify({"response": "Sorry, I'm having trouble responding right now. Please try again shortly."}), 502

    output_text = getattr(completion, "output_text", None)
    if output_text is None:
        try:
            output_text = completion.output[0].content[0].text
        except Exception:
            output_text = ""

    session["conversation"].append({"role": "assistant", "content": output_text})
    session.modified = True

    return jsonify({"response": output_text})


if __name__ == "__main__":
    app.run(debug=True, port=5001)