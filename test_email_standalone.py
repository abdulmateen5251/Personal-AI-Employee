#!/usr/bin/env python3
"""
Standalone test script to verify email configuration.
Uses .env variables only (no credentials.json dependency).
"""
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

EMAIL_CONFIG = {
    'smtp_server': os.getenv("SMTP_SERVER", "smtp.gmail.com"),
    'smtp_port': int(os.getenv("SMTP_PORT", "587")),
    'sender_email': os.getenv("SENDER_EMAIL", ""),
    'sender_password': os.getenv("SENDER_PASSWORD", ""),
    'recipient_email': os.getenv("RECIPIENT_EMAIL", ""),
}

def send_test_email():
    """Send a test email"""
    try:
        sender = EMAIL_CONFIG['sender_email']
        password = EMAIL_CONFIG['sender_password']
        normalized_password = password.replace(" ", "").replace("-", "") if password else ""
        recipient = EMAIL_CONFIG['recipient_email'] or sender
        
        if not sender or not normalized_password:
            print("❌ Email credentials not configured")
            print("\nRequired environment variables:")
            print("  - SENDER_EMAIL: Email address to send from")
            print("  - SENDER_PASSWORD: Email account password or app password")
            print("  - RECIPIENT_EMAIL: Email address to send to (optional, defaults to SENDER_EMAIL)")
            print("\nAdd these to your .env file")
            return False
        
        print(f"📧 Sending test email...")
        print(f"   From: {sender}")
        print(f"   To: {recipient}")
        
        # Create email
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = recipient
        msg['Subject'] = f"Test Email from QAPC - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>✅ Test Email from QAPC System</h2>
                <p>This is a test email to verify your email configuration is working correctly.</p>
                
                <table style="border-collapse: collapse; width: 100%; margin: 20px 0;">
                    <tr style="background-color: #f2f2f2;">
                        <td style="border: 1px solid #ddd; padding: 8px; font-weight: bold;">Test Status:</td>
                        <td style="border: 1px solid #ddd; padding: 8px;">✅ Email delivery successful</td>
                    </tr>
                    <tr>
                        <td style="border: 1px solid #ddd; padding: 8px; font-weight: bold;">Timestamp:</td>
                        <td style="border: 1px solid #ddd; padding: 8px;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</td>
                    </tr>
                    <tr style="background-color: #f2f2f2;">
                        <td style="border: 1px solid #ddd; padding: 8px; font-weight: bold;">Sender:</td>
                        <td style="border: 1px solid #ddd; padding: 8px;">{sender}</td>
                    </tr>
                    <tr>
                        <td style="border: 1px solid #ddd; padding: 8px; font-weight: bold;">SMTP Server:</td>
                        <td style="border: 1px solid #ddd; padding: 8px;">{EMAIL_CONFIG['smtp_server']}:{EMAIL_CONFIG['smtp_port']}</td>
                    </tr>
                </table>
                
                <p style="color: #666; font-size: 12px;">
                    Your email integration is working correctly. You can now proceed with automated email notifications.
                </p>
            </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        # Send email
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        server.starttls()
        server.login(sender, normalized_password)
        server.send_message(msg)
        server.quit()
        
        print("✅ Test email sent successfully!")
        print(f"\nCheck your email inbox ({recipient}) for the test message.")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print("❌ Authentication failed")
        print("   Verify your SENDER_EMAIL and SENDER_PASSWORD are correct")
        print("   For Gmail: Use an App Password, not your regular password")
        print("   Also ensure 2-Step Verification is enabled on your Google account")
        print(f"   SMTP details: code={getattr(e, 'smtp_code', 'unknown')}")
        return False
    except ConnectionError as e:
        print(f"❌ Connection error: {e}")
        print(f"   Cannot connect to {EMAIL_CONFIG['smtp_server']}:{EMAIL_CONFIG['smtp_port']}")
        return False
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return False

def check_configuration():
    """Check if email configuration is set up (.env only)"""
    print("📋 Email Configuration Check")
    print("=" * 50)
    print("Mode: .env only (SMTP, no credentials.json)")
    
    config_items = {
        'SMTP Server': EMAIL_CONFIG['smtp_server'],
        'SMTP Port': EMAIL_CONFIG['smtp_port'],
        'Sender Email': EMAIL_CONFIG['sender_email'] or '(not set)',
        'Sender Password': '(set)' if EMAIL_CONFIG['sender_password'] else '(not set)',
        'Recipient Email': EMAIL_CONFIG['recipient_email'] or '(defaults to sender)',
    }
    
    for key, value in config_items.items():
        status = '✓' if value and value != '(not set)' else '✗'
        print(f"{status} {key}: {value}")
    
    print()
    return EMAIL_CONFIG['sender_email'] and EMAIL_CONFIG['sender_password']

def main():
    print("🧪 Email Integration Test")
    print("=" * 50)
    print()
    
    # Check configuration
    if not check_configuration():
        print("\n⚠️  Email configuration incomplete. Setup required:")
        print("\n1. Edit or create .env file in the project root")
        print("2. Add the following variables:")
        print("   SMTP_SERVER=smtp.gmail.com")
        print("   SMTP_PORT=587")
        print("   SENDER_EMAIL=your-email@gmail.com")
        print("   SENDER_PASSWORD=your-app-password")
        print("   RECIPIENT_EMAIL=recipient@example.com  (optional)")
        print("\n3. For Gmail, generate an App Password:")
        print("   - Go to: https://myaccount.google.com/apppasswords")
        print("   - Create password for 'Mail' and device 'Windows Computer'")
        print("   - Use the generated password as SENDER_PASSWORD")
        return
    
    print("\n✓ Configuration found. Testing email delivery...\n")
    
    # Send test email
    if send_test_email():
        print("\n✅ Email integration is ready to use!")
    else:
        print("\n❌ Email integration test failed. Please check your configuration.")

if __name__ == "__main__":
    main()
