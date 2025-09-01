import logging
import functions_framework

from services.parser import parse_webhook_data
from services.gemini import generate
from services.slack import send_slack_notification

logging.basicConfig(level=logging.INFO)

@functions_framework.http
def youtube_webhook(request):
    if request.method == 'GET':
        logging.info("GET: received get request")
        challenge = request.args.get('hub.challenge')
        if challenge:
            return challenge, 200, {'Content-Type': 'text/plain'}
        else:
            return "This endpoint is for YouTube Webhooks.", 200

    elif request.method == 'POST':
        logging.info("POST: received post request")
        video_data = parse_webhook_data(request.data)

        if not video_data:
            return "Invalid or incomplete webhook data", 400

        logging.info("---------------------------")
        logging.info(f"Title: {video_data['title']}")
        logging.info(f"Video ID: {video_data['video_id']}")
        logging.info(f"Channel ID: {video_data['channel_id']}")
        logging.info(f"Published: {video_data['published']}")
        logging.info("---------------------------")

        video_uri = f"https://www.youtube.com/watch?v={video_data['video_id']}"
        prompt = "다음 YouTube 영상 URI에서 영상의 제목과 설명에 '확률형 아이템 포함' 이라는 문구가 정확히 포함되어 있는지 여부를 판단하여 포함인 경우 'True' 또는 미포함 인 경우 'False' 으로만 답변해주세요."
        
        try:
            response_text = generate(video_uri, prompt)
            logging.info(f"Gemini Response: {response_text}")

            is_included = response_text.strip() == "True"
            
            result_message = "포함" if is_included else "미포함"
            message = f"영상 제목: {video_data['title']}\n확률형 아이템 문구: {result_message}\nURL: {video_uri}"
            
            send_slack_notification(message)

        except Exception as e:
            logging.error(f"Error during Gemini generation or Slack notification: {e}")
            return "Internal server error", 500

        return "", 204

    else:
        return "Method Not Allowed", 405
