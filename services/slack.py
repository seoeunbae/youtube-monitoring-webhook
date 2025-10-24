import os
import requests
import logging
import ssl
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter

# This is a workaround for old SSL versions like LibreSSL on macOS
class TLSv12Adapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = requests.packages.urllib3.poolmanager.PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_version=ssl.PROTOCOL_TLSv1_2
        )

logging.basicConfig(level=logging.INFO)
load_dotenv()

def send_slack_notification(message: str):
    webhook_url = os.getenv('SLACK_WEBHOOK_URL')
    logging.info(f"OpenSSL version: {ssl.OPENSSL_VERSION}")
    logging.info(f"Slack webhook URL: {webhook_url}")
    if not webhook_url:
        logging.warning("Slack webhook URL not set. Cannot send notification.")
        return

    try:
        payload = {"text": message}
        
        # Use a session with the custom adapter
        session = requests.Session()
        session.mount('https://', TLSv12Adapter())
        
        response = session.post(webhook_url, json=payload)
        response.raise_for_status()  # HTTP 오류가 있을 경우 예외 발생
        logging.info("Slack notification sent successfully.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error sending Slack notification: {e}")

if __name__ == '__main__':
    # For this test to work, you need to have a valid SLACK_WEBHOOK_URL in your .env file
    send_slack_notification("Hello from the Slack service!")