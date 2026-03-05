#!/usr/bin/env python3
"""
Standalone test script to verify Google Calendar integration.
"""
import os
import json
import base64
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Google Calendar imports
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    print("✓ Google Calendar libraries imported successfully")
except ImportError as e:
    print(f"✗ Failed to import Google Calendar libraries: {e}")
    print("Install with: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
    exit(1)

# Configuration
CALENDAR_CONFIG = {
    'service_account_info': os.getenv("GOOGLE_SERVICE_ACCOUNT_INFO", ""),
    'service_account_info_b64': os.getenv("GOOGLE_SERVICE_ACCOUNT_INFO_B64", ""),
    'service_account_file': os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", os.getenv("GOOGLE_CALENDAR_CREDENTIALS_PATH", "")),
    'calendar_id': os.getenv("GOOGLE_CALENDAR_ID", os.getenv("CALENDAR_ID", "primary")),
    'scopes': ['https://www.googleapis.com/auth/calendar']
}

def create_calendar_service():
    """Initialize Google Calendar service from .env credentials only"""
    service_account_info = CALENDAR_CONFIG['service_account_info']
    service_account_info_b64 = CALENDAR_CONFIG['service_account_info_b64']
    service_account_file = CALENDAR_CONFIG['service_account_file']

    if service_account_info:
        parsed_info = json.loads(service_account_info)
        credentials = service_account.Credentials.from_service_account_info(
            parsed_info,
            scopes=CALENDAR_CONFIG['scopes']
        )
    elif service_account_info_b64:
        decoded_info = base64.b64decode(service_account_info_b64).decode('utf-8')
        parsed_info = json.loads(decoded_info)
        credentials = service_account.Credentials.from_service_account_info(
            parsed_info,
            scopes=CALENDAR_CONFIG['scopes']
        )
    elif service_account_file:
        if not os.path.exists(service_account_file):
            raise FileNotFoundError(
                f"Service account file not found: {service_account_file}"
            )
        credentials = service_account.Credentials.from_service_account_file(
            service_account_file,
            scopes=CALENDAR_CONFIG['scopes']
        )
    else:
        raise ValueError(
            "Missing service account credentials in .env. "
            "Set GOOGLE_SERVICE_ACCOUNT_INFO (raw JSON string) or "
            "GOOGLE_SERVICE_ACCOUNT_INFO_B64 (base64-encoded JSON) or "
            "GOOGLE_SERVICE_ACCOUNT_FILE / GOOGLE_CALENDAR_CREDENTIALS_PATH."
        )

    return build('calendar', 'v3', credentials=credentials)

def test_calendar_event():
    """Create a test calendar event"""
    try:
        service = create_calendar_service()
        
        # Create test event 1 hour from now
        start_time = datetime.now() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=1)
        
        event = {
            'summary': 'mateen Test Appointment - Please Delete',
            'description': 'Test appointment from calendar integration test. Safe to delete.',
            'location': 'Remote Test',
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'UTC',
            },
            'visibility': 'public',
            'transparency': 'opaque',
            'reminders': {'useDefault': True}
        }
        
        print(f"Creating test event for {start_time.strftime('%Y-%m-%d at %H:%M')}")
        created_event = service.events().insert(
            calendarId=CALENDAR_CONFIG['calendar_id'], 
            body=event,
            sendUpdates='none'
        ).execute()
        
        return {
            'success': True,
            'event_id': created_event['id'],
            'event_link': created_event.get('htmlLink', ''),
            'message': f"Test appointment created successfully for {start_time.strftime('%B %d, %Y at %I:%M %p')}"
        }
        
    except HttpError as e:
        return {
            'success': False,
            'error': f"Google Calendar API error: {str(e)}",
            'message': "Failed to create test appointment due to API error."
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': "Failed to create test appointment."
        }

def main():
    print("🧪 Google Calendar Integration Test")
    print("=" * 50)
    print(f"Calendar ID: {CALENDAR_CONFIG['calendar_id']}")
    print("Credentials Source: .env")

    # Check if credentials are in environment
    file_exists = bool(CALENDAR_CONFIG['service_account_file']) and os.path.exists(
        CALENDAR_CONFIG['service_account_file']
    )

    if (
        CALENDAR_CONFIG['service_account_info']
        or CALENDAR_CONFIG['service_account_info_b64']
        or file_exists
    ):
        print("✓ Service account credentials found in .env")
    else:
        print("✗ Service account credentials not found in .env")
        if CALENDAR_CONFIG['service_account_file']:
            print(f"   File not found: {CALENDAR_CONFIG['service_account_file']}")
        print("\nSetup required:")
        print("1. Create a service account in Google Cloud Console")
        print("2. Get the JSON key content")
        print("3. Put it in .env as GOOGLE_SERVICE_ACCOUNT_INFO (or GOOGLE_SERVICE_ACCOUNT_INFO_B64)")
        print("   OR set GOOGLE_SERVICE_ACCOUNT_FILE / GOOGLE_CALENDAR_CREDENTIALS_PATH")
        print("4. Share your Google Calendar with the service account email")
        print("5. Set GOOGLE_CALENDAR_ID in .env")
        return
    
    try:
        result = test_calendar_event()
        
        if result['success']:
            print("\n✅ SUCCESS: Calendar integration is working!")
            print(f"Event ID: {result['event_id']}")
            print(f"Message: {result['message']}")
            if result['event_link']:
                print(f"Event Link: {result['event_link']}")
            print("\n📧 Check your Google Calendar for the test appointment!")
        else:
            print(f"\n❌ FAILED: {result['message']}")
            print(f"Error: {result['error']}")
            
    except Exception as e:
        print(f"\n❌ EXCEPTION: {e}")

if __name__ == "__main__":
    main()
