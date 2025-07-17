from twilio.rest import Client
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get Twilio credentials from environment
account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
phone_number = os.environ.get("TWILIO_PHONE_NUMBER")

print(f"TWILIO_ACCOUNT_SID: {account_sid}")
print(f"TWILIO_AUTH_TOKEN: {auth_token[:4]}...{auth_token[-4:]}")  # Show only first and last 4 chars for security
print(f"TWILIO_PHONE_NUMBER: {phone_number}")
try:
    client = Client(account_sid, auth_token)
    print("Twilio client initialized successfully")
    
    # Try to fetch account info to verify credentials
    account = client.api.accounts(account_sid).fetch()
    print(f"Account status: {account.status}")
    print("Twilio credentials are valid!")
except Exception as e:
    print(f"Error: {e}")
    print("Twilio credentials are invalid or there's a connection issue.") 