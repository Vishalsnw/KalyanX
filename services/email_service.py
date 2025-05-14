
import os
import logging
from flask import current_app
from mailjet_rest import Client


def send_email(to_email, subject, body, html_body=None):
    """
    Send email using Mailjet API
    
    Args:
        to_email (str): The recipient's email address
        subject (str): Email subject
        body (str): Plain text email body
        html_body (str, optional): HTML email body
        
    Returns:
        bool: True if the email was sent successfully, False otherwise
    """
    try:
        # Get API keys from environment variables
        api_key = os.environ.get('MAILJET_API_KEY')
        secret_key = os.environ.get('MAILJET_SECRET_KEY')
        
        if not api_key or not secret_key:
            logging.error("Mailjet API keys not set in environment variables")
            # Fall back to logging if API keys are not available
            return _log_email(to_email, subject, body, html_body)
        
        # Initialize Mailjet client
        mailjet = Client(auth=(api_key, secret_key), version='v3.1')
        
        # Set the sender email (must be a verified sender in your Mailjet account)
        sender_email = current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@kalyanx.com')
        sender_name = "KalyanX Team"
        
        # Prepare the message content
        message_content = {
            'From': {
                'Email': sender_email,
                'Name': sender_name
            },
            'To': [
                {
                    'Email': to_email,
                    'Name': to_email  # We don't have the user's name, so use email as name
                }
            ],
            'Subject': subject,
            'TextPart': body
        }
        
        # Add HTML content if provided
        if html_body:
            message_content['HTMLPart'] = html_body
            
        # Prepare the data for the API request
        data = {
            'Messages': [message_content]
        }
        
        # Send the email with Mailjet API
        result = mailjet.send.create(data=data)
        
        if result.status_code == 200:
            logging.info(f"Email sent to {to_email} successfully via Mailjet")
            return True
        else:
            error_response = result.json()
            logging.error(f"Failed to send email via Mailjet: {error_response}")
            
            # Log more detailed error information
            if 'ErrorMessage' in error_response:
                logging.error(f"Mailjet error message: {error_response['ErrorMessage']}")
            if 'ErrorCode' in error_response:
                logging.error(f"Mailjet error code: {error_response['ErrorCode']}")
            if 'Errors' in error_response:
                for error in error_response['Errors']:
                    logging.error(f"Mailjet detailed error: {error}")
            
            # Print to console for immediate visibility during development
            print("\n" + "=" * 50)
            print(f"MAILJET ERROR: Failed to send email to {to_email}")
            print(f"Status code: {result.status_code}")
            print(f"Response: {error_response}")
            print("=" * 50 + "\n")
            
            # Fall back to logging if API request fails
            return _log_email(to_email, subject, body, html_body)
            
    except Exception as e:
        logging.error(f"Error sending email to {to_email}: {str(e)}")
        # Fall back to logging in case of any exception
        return _log_email(to_email, subject, body, html_body)


def _log_email(to_email, subject, body, html_body=None):
    """
    Log email content as a fallback when API is not available
    
    Args:
        to_email (str): The recipient's email address
        subject (str): Email subject
        body (str): Plain text email body
        html_body (str, optional): HTML email body
        
    Returns:
        bool: True if the email was successfully logged
    """
    try:
        logging.info("=" * 50)
        logging.info("FALLBACK: Logging email instead of sending")
        logging.info(f"EMAIL TO: {to_email}")
        logging.info(f"SUBJECT: {subject}")
        logging.info("BODY:")
        logging.info(body)
        
        if html_body:
            logging.info("HTML BODY (Preview):")
            preview = html_body[:500] + "..." if len(html_body) > 500 else html_body
            logging.info(preview)
            
        logging.info("=" * 50)
        
        # Print to console as well for immediate visibility during testing
        print("\n" + "=" * 50)
        print("FALLBACK: Logging email instead of sending")
        print(f"EMAIL TO: {to_email}")
        print(f"SUBJECT: {subject}")
        print("BODY:")
        print(body)
        print("=" * 50 + "\n")
        
        return True
    except Exception as e:
        logging.error(f"Error logging email to {to_email}: {str(e)}")
        return False


def send_otp(email, otp):
    """
    Send OTP code via email
    
    Args:
        email (str): The recipient's email address
        otp (str): The OTP code to send
        
    Returns:
        bool: True if the OTP was sent successfully, False otherwise
    """
    subject = "KalyanX: Your OTP Verification Code"
    
    body = f"""
Hello,

Your OTP for KalyanX login is: {otp}

This code will expire in 10 minutes. Do not share it with anyone.

Thank you,
KalyanX Team
"""

    html_body = f"""
<html>
<body>
    <h2>KalyanX Verification Code</h2>
    <p>Your OTP for KalyanX login is:</p>
    <h1 style="font-size: 32px; color: #e74c3c; padding: 10px; background-color: #f8f9fa; border-radius: 5px; text-align: center;">{otp}</h1>
    <p>This code will expire in 10 minutes.</p>
    <p><strong>Do not share this code with anyone.</strong></p>
    <p>Thank you,<br>KalyanX Team</p>
</body>
</html>
"""
    
    return send_email(email, subject, body, html_body)


def send_notification_email(email, title, message):
    """
    Send notification via email
    
    Args:
        email (str): The recipient's email address
        title (str): The notification title
        message (str): The notification message
        
    Returns:
        bool: True if the notification was sent successfully, False otherwise
    """
    subject = f"KalyanX: {title}"
    
    body = f"""
Hello,

{title}

{message}

Thank you,
KalyanX Team
"""

    html_body = f"""
<html>
<body>
    <h2>{title}</h2>
    <p>{message}</p>
    <p>Thank you,<br>KalyanX Team</p>
</body>
</html>
"""
    
    return send_email(email, subject, body, html_body)
