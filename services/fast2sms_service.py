import os
import requests
import logging

# Environment variable for Fast2SMS API key
FAST2SMS_API_KEY = os.environ.get("FAST2SMS_API_KEY")

def send_sms(mobile_number, message):
    """
    Send SMS using Fast2SMS API
    
    Args:
        mobile_number (str): The recipient's mobile number (10 digits)
        message (str): The message content to send
        
    Returns:
        bool: True if the SMS was sent successfully, False otherwise
    """
    # Check if API key is available
    if not FAST2SMS_API_KEY:
        # In development mode, just log the message
        logging.info(f"SMS to {mobile_number}: {message}")
        return True

    # Remove any '+91' prefix if present
    if mobile_number.startswith('+91'):
        mobile_number = mobile_number[3:]
    
    # Remove any spaces or hyphens
    mobile_number = mobile_number.replace(' ', '').replace('-', '')
    
    # Ensure it's a 10-digit number
    if len(mobile_number) != 10 or not mobile_number.isdigit():
        logging.error(f"Invalid mobile number format: {mobile_number}")
        return False
    
    # Fast2SMS API endpoint
    url = "https://www.fast2sms.com/dev/bulkV2"
    
    # Prepare payload
    payload = {
        "message": message,
        "language": "english",
        "route": "v3",  # Promotional route
        "numbers": mobile_number,
    }
    
    # Prepare headers
    headers = {
        "authorization": FAST2SMS_API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        # Make the API request
        response = requests.post(url, json=payload, headers=headers)
        response_data = response.json()
        
        # Check if the SMS was sent successfully
        if response.status_code == 200 and response_data.get("return") == True:
            logging.info(f"SMS sent successfully to {mobile_number}")
            return True
        else:
            logging.error(f"Failed to send SMS to {mobile_number}: {response_data}")
            return False
    except Exception as e:
        logging.error(f"Error sending SMS to {mobile_number}: {str(e)}")
        return False


def send_otp(mobile_number, otp):
    """
    Send OTP code via SMS
    
    Args:
        mobile_number (str): The recipient's mobile number
        otp (str): The OTP code to send
        
    Returns:
        bool: True if the OTP was sent successfully, False otherwise
    """
    # Use Fast2SMS templated OTP message format to potentially get better rates
    # and faster delivery for transactional messages
    message = f"Your OTP for KalyanX login is {otp}. Valid for 10 minutes. DO NOT share with anyone."
    return send_sms(mobile_number, message)


def send_notification(mobile_number, title, message):
    """
    Send notification via SMS
    
    Args:
        mobile_number (str): The recipient's mobile number
        title (str): The notification title
        message (str): The notification message
        
    Returns:
        bool: True if the notification was sent successfully, False otherwise
    """
    # Format the notification message with title
    sms_content = f"{title}: {message}"
    return send_sms(mobile_number, sms_content)