import logging
import functions_framework
import os
import json
from dotenv import load_dotenv
from services.youtube_parser import parse_youtube_webhook_data
from services.gemini import generate
from services.slack import send_slack_notification
from services.facebook_parser import parse_facebook_webhook
from services.tiktok_parser import verify_tiktok_signature, extract_video_id_from_content

load_dotenv()

FACEBOOK_VERIFY_TOKEN = os.getenv('FACEBOOK_VERIFY_TOKEN')
TIKTOK_CLIENT_SECRET=os.getenv("TIKTOK_CLIENT_SECRET")
# instagram_verify_token = os.getenv('INSTAGRAM_VERIFY_TOKEN')

logging.basicConfig(level=logging.INFO)

@functions_framework.http
def youtube_webhook(request):
    logging.info(request)
    logging.info(request.method)
    logging.info(request.headers)
    logging.info(request.get_data())
    logging.info(request.data)

    if request.method == 'GET':
        logging.info("GET 요청: Webhook 인증을 시작합니다.")
        # Case 1: Facebook 인증 요청 (verify_token이 존재)
        if 'hub.verify_token' in request.args:
            logging.info("Facebook 인증 요청을 감지했습니다.")
            verify_token = request.args.get('hub.verify_token')  
            
            if verify_token == FACEBOOK_VERIFY_TOKEN:
                challenge = request.args.get('hub.challenge')
                logging.info("Facebook 확인 토큰이 일치합니다. challenge를 반환합니다s.")
                return challenge, 200
            else:
                logging.error("Facebook 확인 토큰이 일치하지 않습니다.")
                return "Invalid verify token", 403
        # Case 2: YouTube 인증 요청 (verify_token은 없고 challenge만 존재)
        elif 'hub.challenge' in request.args:
            logging.info("YouTube 인증 요청을 감지했습니다.")
            challenge = request.args.get('hub.challenge')
            logging.info("YouTube challenge를 반환합니다.")
            return challenge, 200, {'Content-Type': 'text/plain'}
        # Case 3: 그 외의 GET 요청
        else:
            logging.warning("인증 파라미터가 없는 GET 요청입니다.")
            return "Webhook Endpoint", 200     
    elif request.method == 'POST':
        logging.info("POST 요청: 새로운 데이터를 수신했습니다.")
        print(request.headers)
        is_tiktok_webhook = 'TikTok-Signature' in request.headers
        is_youtube_webhook = request.headers.get('Content-Type') == 'application/atom+xml' # YouTube usually sends Link header with hub.topic
        is_facebook_webhook = 'X-Hub-Signature-256' in request.headers

        content_type = request.headers.get('Content-Type', '')
    
        logging.info(request.data)
        if is_tiktok_webhook:
            logging.info("Detected TikTok webhook.")
            # Verify TikTok signature
            if not verify_tiktok_signature(request, TIKTOK_CLIENT_SECRET):
                return "Unauthorized: Invalid TikTok signature", 401
            
            tiktok_payload = json.loads(request.data)
            event_type = tiktok_payload.get('event')
            
            if event_type == 'tiktok.ping': # Example event type
                return "ok", 200 
            elif event_type == 'video.publish.complete': # Example event type
                # tiktok_video_data = parse_tiktok_webhook_data(request.data)
                # TikTok webhooks usually send JSON
            
                # Example parsing - adjust according to actual TikTok event structure
                content = tiktok_payload.get('content', {})
                
                video_id = extract_video_id_from_content(content)
                published = tiktok_payload.get('create_time')
                tiktok_channel_name = os.getenv('TIKTOK_CHANNEL_NAME')
                if not video_uri:
                    return "Invalid or incomplete TikTok webhook video_uri", 400

                logging.info("--------TIktok 정보-------------------")
    
                video_uri = f"https://www.tiktok.com/@{tiktok_channel_name}/video/{video_id}" # TikTok video URL format
                prompt = "다음 TikTok 영상 URI에서 영상의 제목과 설명에 '확률형 아이템 포함' 이라는 문구가 정확히 포함되어 있는지 여부를 판단하여 포함인 경우 'True' 또는 미포함 인 경우 'False' 으로만 답변해주세요."

                try:
                    response_text = generate(video_uri, prompt, "")
                    logging.info(f"Gemini Response (TikTok): {response_text}")

                    is_included = response_text.strip() == "True"
                    result_message = "포함" if is_included else "미포함"
                    
                    message = (
                        f"**TikTok 영상 업데이트** 🎥\n"
                        f"채널 명: Tiktok\n"
                        f"확률형 아이템 문구: {result_message}\n"
                        f"영상 URL: {video_uri}\n"
                        f"채널명: {tiktok_channel_name}\n"
                        f"영상 업로드 시간: {published}"
                    )
                    
                    send_slack_notification(message)

                except Exception as e:
                    logging.error(f"Error during Gemini generation or Slack notification for TikTok: {e}")
                    return "Internal server error for TikTok webhook", 500

            return "slack send success", 204 # No Content, indicating successful processing
        elif is_facebook_webhook:
            logging.info("Detected Facebook webhook.")

            facebook_video_data = parse_facebook_webhook(request.get_data())

            if not facebook_video_data:
                return "Invalid or incomplete Facebook webhook data", 400

            logging.info("---------------------------")
            logging.info(f"Facebook Title: {facebook_video_data['title']}")
            logging.info(f"Facebook Video ID: {facebook_video_data['video_id']}")
            logging.info(f"Facebook Post ID: {facebook_video_data['post_id']}")
            logging.info(f"Facebook Page ID: {facebook_video_data['page_id']}")
            logging.info(f"Facebook Published: {facebook_video_data['published']}")
            logging.info(f"Facebook URL: {facebook_video_data['message']}")

            video_uri = facebook_video_data['url'] # Use the URL derived from parsing
            prompt = "다음 Facebook 영상 URI에서 영상의 제목과 설명에 '확률형 아이템 포함' 이라는 문구가 정확히 포함되어 있는지 여부를 판단하여 포함인 경우 'True' 또는 미포함 인 경우 'False' 으로만 답변해주세요."

            try:
                response_text = generate(video_uri, prompt, facebook_video_data['message'])
                logging.info(f"Gemini Response (Facebook): {response_text}")

                is_included = response_text.strip() == "True"
                result_message = "포함" if is_included else "미포함"
                
                message = (
                    f"**Facebook 영상 업데이트** 📘\n"
                    f"영상 제목: {facebook_video_data['title']}\n"
                    f"확률형 아이템 문구: {result_message}\n"
                    f"영상 URL: {video_uri}\n"
                    f"페이지 ID: {facebook_video_data['page_id']}\n"
                    f"영상 업로드 시간: {facebook_video_data['published']}"
                )
                
                send_slack_notification(message)

            except Exception as e:
                logging.error(f"Error during Gemini generation or Slack notification for Facebook: {e}")
                return "Internal server error for Facebook webhook", 500

            return "", 204
        elif is_youtube_webhook:
            logging.info("Detected YouTube webhook.")
            video_data = parse_youtube_webhook_data(request.get_data())

            if not video_data:
                return "Invalid or incomplete YouTube webhook data", 400

            logging.info("---------------------------")
            logging.info(f"YouTube Title: {video_data['title']}")
            logging.info(f"YouTube Video ID: {video_data['video_id']}")
            logging.info(f"YouTube Channel ID: {video_data['channel_id']}")
            logging.info(f"YouTube Published: {video_data['published']}")

            video_uri = f"https://www.youtube.com/watch?v={video_data['video_id']}"
            prompt = "다음 YouTube 영상 URI에서 영상의 제목과 설명에 '확률형 아이템 포함' 이라는 문구가 정확히 포함되어 있는지 여부를 판단하여 포함인 경우 'True' 또는 미포함 인 경우 'False' 으로만 답변해주세요."
            
            try:
                response_text = generate(video_uri, prompt, "")
                logging.info(f"Gemini Response (YouTube): {response_text}")

                is_included = response_text.strip() == "True"
                result_message = "포함" if is_included else "미포함"
                
                message = (
                        f"**Facebook 영상 업데이트** 📘\n"
                        f"영상 제목: {video_data['title']}\n"
                        f"확률형 아이템 문구: {result_message}\n"
                        f"영상 URL: {video_data}\n"
                        f"페이지 ID: {video_data['page_id']}\n"
                        f"영상 업로드 시간: {video_data['published']}"
                    )
                    
                # message = f" 영상 제목: {video_data['title']}\n 확률형 아이템 문구: {result_message}\n 영상 URL: {video_uri} \n 영상 업로드 시간: {video_data['published']}"
                
                send_slack_notification(message)
            except Exception as e:
                logging.error(f"Error during Gemini generation or Slack notification for Facebook: {e}")
                return "Internal server error for Facebook webhook", 500      
            return "", 204
        else:
            logging.error("Unsupported channel")
    else:
        return "Method Not Allowed", 405
