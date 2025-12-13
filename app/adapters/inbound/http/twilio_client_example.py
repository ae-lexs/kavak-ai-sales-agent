"""
Example: Using Twilio credentials from environment variables.

This is a minimal example showing how to initialize a Twilio client
using the credentials loaded from .env file via python-dotenv.

Note: This file is for reference only. The actual webhook implementation
does not require a Twilio client (it only validates signatures and generates TwiML).
"""

import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Read Twilio credentials from environment
twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER")

# Example: Initialize Twilio client (requires twilio package)
# Uncomment and install: pip install twilio
#
# from twilio.rest import Client
#
# if twilio_account_sid and twilio_auth_token:
#     client = Client(twilio_account_sid, twilio_auth_token)
#     # Use client to send messages, etc.
# else:
#     raise ValueError("Twilio credentials not found in environment variables")

# Example: Using credentials directly (current implementation)
if twilio_auth_token:
    print(f"Twilio Auth Token loaded: {twilio_auth_token[:10]}...")
else:
    print("Warning: TWILIO_AUTH_TOKEN not set in .env file")

if twilio_account_sid:
    print(f"Twilio Account SID loaded: {twilio_account_sid}")
else:
    print("Warning: TWILIO_ACCOUNT_SID not set in .env file")

if twilio_whatsapp_number:
    print(f"Twilio WhatsApp Number: {twilio_whatsapp_number}")
else:
    print("Warning: TWILIO_WHATSAPP_NUMBER not set in .env file")
