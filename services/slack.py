import os
import requests
import logging
from dotenv import load_dotenv

load_dotenv()

def send_slack_notification(message: str):
    webhook_url = os.getenv('SLACK_WEBHOOK_URL')
    logging.info(f"Slack webhook URL: {webhook_url}")
    if not webhook_url:
        logging.warning("Slack webhook URL not set. Cannot send notification.")
        return 
    try:
        payload = {"text": message}
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status() # HTTP 오류가 있을 경우 예외 발생
        logging.info("Slack notification sent successfully.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error sending Slack notification: {e}")
