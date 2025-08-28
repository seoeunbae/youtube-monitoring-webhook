from dotenv import load_dotenv
import os
import xmltodict
import functions_framework
from google import genai
from google.genai import types
import requests
import logging

logging.basicConfig(level=logging.INFO)

load_dotenv()

@functions_framework.http
def youtube_webhook(request):
    logging.info(f"Request method: {request.method}")
    logging.info(f"Request method: {request.headers}")
    if request.method == 'GET':
        logging.info("GET: recevie get request ")
        challenge = request.args.get('hub.challenge')
        if challenge:
            return challenge, 200, {'Content-Type': 'text/plain'}
        else:
            return "This endpoint is for YouTube Webhooks.", 200
    elif request.method == 'POST':
        logging.info("POST: recevie post request")
        logging.info(f"Headers: {request.headers}")
        xml_data = request.get_data()
        
        if not xml_data:
            logging.warning("POST request received with empty payload.")
            return "Empty payload", 400
        try:
            xml_data = request.data.decode('utf-8')
            data = xmltodict.parse(xml_data)
            entry = data.get('feed', {}).get('entry')
            if entry:
                video_id = entry.get('yt:videoId')
                channel_id = entry.get('yt:channelId')
                title = entry.get('title')
                published = entry.get('published')

                
                if not all([video_id, channel_id, title, published]):
                    logging.warning("Incomplete data in 'entry'.")
                    return "Incomplete data in 'entry'", 400

                logging.info("---------------------------")
                logging.info(f"Title: {title}")
                logging.info(f"Video ID: {video_id}")
                logging.info(f"Channel ID: {channel_id}")
                logging.info(f"Published: {published}")
                
                video_uri = f"https://www.youtube.com/watch?v={video_id}"
                prompt = "다음 YouTube 영상 URI에서 영상의 제목과 설명에 '확률형 아이템 포함' 이라는 문구가 정확히 포함되어 있는지 여부를 판단하여 포함인 경우 'True' 또는 미포함 인 경우 'False' 으로만 답변해주세요."
                response = generate(video_uri, prompt)
                logging.info(response) 
                
                if response.strip() == "True":
                    message = "Title : "+ title +" , Video ID : "+ video_id + ", Channel ID : " + channel_id +", Published : "+ published + " 에 해당 문구가 존재합니다."
                    send_slack_notification(message)
                else:
                    message = "Title : "+ title + ", Video ID : "+ video_id + ", Channel ID : " + channel_id + ", Published : " + published + " 에 해당 문구가 존재하지 않습니다."
                    send_slack_notification(message)
                return "", 204
            

            else:
                logging.warning("No 'entry' found in the XML data.")
                return "Invalid XML data: 'entry' not found", 400
                
        except Exception as e:
            logging.error(f"Error parsing XML: {e}")
            return "Invalid XML data", 400


def generate(file_uri, prompt):
  client = genai.Client(
      vertexai=True,
      project="test-for-monitoring-webhook",
      location="global",
  )

  msg1_text1 = types.Part.from_text(text=prompt)
  msg1_video1 = types.Part.from_uri(
      file_uri=file_uri,
      mime_type="video/*",
  )

  model = "gemini-2.5-pro"
  contents = [
    types.Content(
      role="user",
      parts=[
        msg1_text1,
        msg1_video1
      ]
    ),
  ]

  generate_content_config = types.GenerateContentConfig(
    temperature = 1,
    top_p = 0.95,
    seed = 0,
    max_output_tokens = 65535,
    safety_settings = [types.SafetySetting(
      category="HARM_CATEGORY_HATE_SPEECH",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_DANGEROUS_CONTENT",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_HARASSMENT",
      threshold="OFF"
    )],
    thinking_config=types.ThinkingConfig(
      thinking_budget=-1,
    ),
  )
  response = client.models.generate_content(
    model = model,
    contents = contents,
    config = generate_content_config,
    )
  return response.text


def send_slack_notification(message: str):
    webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
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