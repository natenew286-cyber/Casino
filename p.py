import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def send_email(sender_email, sender_password, recipient_email, subject, body, attachment_path=None):
    """
    Send an email using Gmail SMTP server.
    
    Args:
        sender_email: Your Gmail address
        sender_password: Your Gmail App Password (not regular password)
        recipient_email: Recipient's email address
        subject: Email subject
        body: Email body text
        attachment_path: Optional path to file attachment
    """
    try:
        # Create message
        message = MIMEMultipart()
        message['From'] = sender_email
        message['To'] = recipient_email
        message['Subject'] = subject
        
        # Add body to email
        message.attach(MIMEText(body, 'plain'))
        
        # Add attachment if provided
        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {os.path.basename(attachment_path)}'
                )
                message.attach(part)
        
        # Create SMTP session
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()  # Enable security
            server.login(sender_email, sender_password)
            
            # Send email
            text = message.as_string()
            server.sendmail(sender_email, recipient_email, text)
        
        print(f"Email sent successfully to {recipient_email}")
        return True
        
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False


# Example usage
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Send an email using Gmail SMTP.')
    parser.add_argument('--recipient', type=str, help='Recipient email address')
    parser.add_argument('--subject', type=str, help='Email subject')
    parser.add_argument('--body', type=str, help='Email body')
    parser.add_argument('--attachment', type=str, help='Path to attachment')

    args = parser.parse_args()

    # Configuration from Env or Args
    SENDER_EMAIL = os.getenv('EMAIL_HOST_USER', 'hammondkakhayanga@gmail.com')
    SENDER_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', 'gulf ccuu xatr eojq')
    
    RECIPIENT_EMAIL = args.recipient or os.getenv('TEST_RECIPIENT_EMAIL', 'hammondkakhayanga@gmail.com')
    
    # Email content
    subject = args.subject or "Test Email from Python"
    body = args.body or """Hello,

This is a test email sent from a Python script using Gmail SMTP.

Best regards,
Python Script"""
    
    print(f"Sending email from {SENDER_EMAIL} to {RECIPIENT_EMAIL}...")

    # Send email (with optional attachment)
    send_email(
        sender_email=SENDER_EMAIL,
        sender_password=SENDER_PASSWORD,
        recipient_email=RECIPIENT_EMAIL,
        subject=subject,
        body=body,
        attachment_path=args.attachment
    )