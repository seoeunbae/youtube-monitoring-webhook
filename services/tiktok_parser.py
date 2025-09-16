import logging
import functions_framework
import hmac
import hashlib
import json
import os # For environment variables like CLIENT_SECRET

from services.youtube_parser import parse_youtube_webhook_data # Renamed for clarity
from services.gemini import generate
from services.slack import send_slack_notification

logging.basicConfig(level=logging.INFO)
TIKTOK_CLIENT_SECRET = os.getenv('TIKTOK_CLIENT_SECRET')


# 개발자 문서에 나온 예시 페이로드
# webhook_payload = {
#   "client_key": "bwo2m45353a6k85",
#   "event": "video.publish.completed",
#   "create_time": 1615338610,
#   "user_openid": "act.example12345Example12345Example",
#   "content": "{\"share_id\":\"video.6974245311675353080.VDCrcMJV\"}"
# }

# 결과:
# 생성된 비디오 URI: https://www.tiktok.com/video/6974245311675353080

def extract_video_id_from_content(content_str):
    """'content' 문자열에서 숫자 비디오 ID를 추출합니다."""
    try:
        content_data = json.loads(content_str)
        share_id = content_data['share_id']
        video_id = share_id.split('.')[1]
        return video_id
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        print(f"비디오 ID를 추출하는 중 오류 발생: {e}")
        return None

def verify_tiktok_signature(request, client_secret):
    """
    Verifies the TikTok webhook signature.
    Returns True if the signature is valid, False otherwise.
    """
    signature_header = request.headers.get('TikTok-Signature')
    if not signature_header:
        logging.warning("TikTok-Signature header missing.")
        return False

    try:
        parts = signature_header.split(',')
        timestamp = None
        signature = None
        for part in parts:
            if part.startswith('t='):
                timestamp = part[2:]
            elif part.startswith('s='):
                signature = part[2:]

        if not timestamp or not signature:
            logging.warning("TikTok-Signature header malformed (missing t or s).")
            return False

        # Construct the signed payload
        signed_payload = f"{timestamp}.{request.get_data().decode('utf-8')}"

        # Calculate the expected signature
        expected_signature = hmac.new(
            client_secret.encode('utf-8'),
            signed_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            logging.warning(f"Signature mismatch. Received: {signature}, Expected: {expected_signature}")
            return False

        # Optional: Check timestamp for replay attacks (e.g., within 5 minutes)
        # current_time = int(time.time())
        # if abs(current_time - int(timestamp)) > 300: # 5 minutes
        #     logging.warning("Timestamp too old, potential replay attack.")
        #     return False

        return True
    except Exception as e:
        logging.error(f"Error during TikTok signature verification: {e}")
        return False
    
    # Placeholder for parsing TikTok webhook data
def parse_tiktok_webhook_data(data):
    """
    Parses TikTok webhook data.
    This function needs to be implemented based on the actual TikTok webhook payload structure.
    For demonstration, it assumes a 'video_id', 'title', 'channel_name', 'published_at' structure.
    """
    try:
        # TikTok webhooks usually send JSON
        tiktok_payload = json.loads(data)
        logging.info(f"TikTok Webhook Payload: {tiktok_payload}")

        # Example parsing - adjust according to actual TikTok event structure
        event_type = tiktok_payload.get('event')
        content = tiktok_payload.get('content', {})

        if event_type == 'video.publish.complete': # Example event type
            video_info = {
                'title': content.get('video_title', 'No Title'),
                'video_id': content.get('video_id', 'No Video ID'),
                'channel_name': content.get('channel_name', 'No Channel Name'), # TikTok might not provide this directly in all events
                'published': content.get('create_time', 'No Publish Time') # This might be a Unix timestamp, requires formatting
            }
            return video_info
        ## 이벤트 추가하기
        logging.warning(f"Unhandled TikTok event type: {event_type}")
        return None

    except json.JSONDecodeError as e:
        logging.error(f"Failed to decode TikTok webhook JSON: {e}")
        return None
    except Exception as e:
        logging.error(f"Error parsing TikTok webhook data: {e}")
        return None