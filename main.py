import os
import random
from dotenv import load_dotenv
import uvicorn
import phonenumbers
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from telethon import TelegramClient, errors
from telethon.tl.functions.contacts import ImportContactsRequest, DeleteContactsRequest
from telethon.tl.types import InputPhoneContact
from contextlib import asynccontextmanager

# Load .env variables
load_dotenv()

default_messages = [
    "Hello! Hope you have a wonderful day! 😊",
    "Hi there! Wishing you lots of smiles today! 😄",
    "Hey! Sending positive vibes your way! ✨",
    "Good day! May your day be as bright as your smile! 🌞",
    "Hello! Remember, you're amazing just the way you are! 💖",
    "Hi! Keep shining and spreading joy! 🌟",
    "Hey there! Hope your day is full of happiness! 🌈",
    "Good vibes only! Have a fantastic day! 🎉",
    "Hello! Stay positive and keep moving forward! 🚀",
    "Hi! Just a little message to brighten your day! ☀️"
]

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
PHONE_NUMBER = os.getenv("PHONE_NUMBER")

client = TelegramClient('session_session', API_ID, API_HASH)

def validate_phone(phone: str) -> str:
    try:
        # Parse phone number (strict=True enforces country code)
        parsed = phonenumbers.parse(phone, None)
        # Check if valid number
        if not phonenumbers.is_valid_number(parsed):
            raise ValueError("Invalid phone number.")
        # Return formatted E.164 number (standardized format)
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Phone validation error: {str(e)}")
    
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting Telegram client...")
    await client.start(phone=PHONE_NUMBER)
    yield
    print("Disconnecting Telegram client...")
    await client.disconnect()

app = FastAPI(lifespan=lifespan, title="Telegram Phone Checker API")

class PhoneNumberRequest(BaseModel):
    phone: str
    message: Optional[str] = None  # Optional message field

@app.post("/check-and-message")
async def check_and_message(data: PhoneNumberRequest):
    # Validate and normalize phone number first
    phone = validate_phone(data.phone.strip())
    msg = data.message.strip() if data.message else random.choice(default_messages)

    try:
        contacts = [InputPhoneContact(client_id=0, phone=phone, first_name='Check', last_name='User')]
        result = await client(ImportContactsRequest(contacts))

        if result.users:
            user = result.users[0]

            # Send message (default or custom)
            await client.send_message(user, msg)

            # Clean up imported contact
            await client(DeleteContactsRequest(id=[user.id]))

            return {
                "phone": phone,
                "found": True,
                "user_id": user.id,
                "username": user.username,
                "message_sent": msg
            }
        else:
            return {
                "phone": phone,
                "found": False,
                "message": "Phone number not registered on Telegram"
            }
    except errors.FloodWaitError as e:
        raise HTTPException(status_code=429, detail=f"Flood wait error. Retry after {e.seconds} seconds.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
