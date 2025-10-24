import logging
import functions_framework
import os
import threading
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

# 메모리 내에서 처리된 이벤트 ID를 추적하기 위한 세트 (간단한 중복 방지용)
# 더 강력한 중복 방지를 위해서는 Redis나 Firestore 같은 외부 저장소 사용을 권장합니다.
PROCESSED_EVENTS = set()

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
        # Gemini API 호출과 같은 오래 걸리는 작업을 백그라운드에서 처리합니다.
        # 이렇게 하면 Webhook 제공자에게 빠르게 응답하여 timeout 및 재시도를 방지할 수 있습니다.
        thread = threading.Thread(target=handle_webhook, args=(request,))
        thread.start()

        # 요청을 성공적으로 수신했으며 비동기적으로 처리 중임을 알립니다.
        return "Accepted", 202
    else:
        return "Method Not Allowed", 405

def handle_webhook(request):
    """백그라운드에서 실제 웹훅 처리 로직을 수행합니다."""
    headers = request.headers
    data = request.get_data()

    content_type = headers.get('Content-Type', '')
    is_tiktok_webhook = 'TikTok-Signature' in headers
    is_youtube_webhook = 'application/atom+xml' in content_type
    is_facebook_webhook = 'X-Hub-Signature-256' in headers
    
    if is_tiktok_webhook:
        logging.info("Detected TikTok webhook.")
        if not verify_tiktok_signature(request, TIKTOK_CLIENT_SECRET):
            logging.error("Unauthorized: Invalid TikTok signature")
            return
        
        tiktok_payload = json.loads(data)
        event_type = tiktok_payload.get('event')
        
        # 멱등성 키로 사용할 고유 ID (예: create_time + share_id)
        idempotency_key = f"tiktok-{tiktok_payload.get('create_time')}-{tiktok_payload.get('content', {}).get('share_id')}"
        if idempotency_key in PROCESSED_EVENTS:
            logging.info(f"Skipping already processed TikTok event: {idempotency_key}")
            return
        PROCESSED_EVENTS.add(idempotency_key)

        if event_type == 'tiktok.ping':
            logging.info("Received TikTok ping event.")
            return
        elif event_type == 'video.publish.complete':
            content = tiktok_payload.get('content', {})
            video_id = extract_video_id_from_content(content)
            if not video_id:
                logging.error("Could not extract video_id from TikTok webhook.")
                return

            published = tiktok_payload.get('create_time')
            tiktok_channel_name = os.getenv('TIKTOK_CHANNEL_NAME')
            video_uri = f"https://www.tiktok.com/@{tiktok_channel_name}/video/{video_id}"
            prompt = "다음 TikTok 영상 URI에서 영상의 제목과 설명에 '확률형 아이템 포함' 이라는 문구가 정확히 포함되어 있는지 여부를 판단하여 포함인 경우 'True' 또는 미포함 인 경우 'False' 으로만 답변해주세요."

            try:
                response_text = generate(video_uri, prompt, "")
                is_included = response_text.strip() == "True"
                result_message = "포함" if is_included else "미포함"
                
                message = (
                    f"**TikTok 영상 업데이트** 🎥\n"
                    f"채널 명: {tiktok_channel_name}\n"
                    f"확률형 아이템 문구: {result_message}\n"
                    f"영상 URL: {video_uri}\n"
                    f"영상 업로드 시간: {published}"
                )
                send_slack_notification(message)
                return "ok", 200
            except Exception as e:
                logging.error(f"Error processing TikTok webhook: {e}")

    elif is_facebook_webhook:
        logging.info("Detected Facebook webhook.")
        facebook_video_data = parse_facebook_webhook(json.loads(data))
        if not facebook_video_data:
            logging.warning("Invalid or incomplete Facebook webhook data")
            return

        # 멱등성 키로 사용할 고유 ID (예: post_id)
        idempotency_key = f"facebook-{facebook_video_data.get('post_id')}"
        if idempotency_key in PROCESSED_EVENTS:
            logging.info(f"Skipping already processed Facebook event: {idempotency_key}")
            return
        PROCESSED_EVENTS.add(idempotency_key)

        video_uri = facebook_video_data.get('media_url')
        if not video_uri:
            logging.error("No media_url in Facebook webhook data.")
            return

        prompt = "다음 Facebook 영상 URI에서 영상의 제목과 설명에 '확률형 아이템 포함' 이라는 문구가 정확히 포함되어 있는지 여부를 판단하여 포함인 경우 'True' 또는 미포함 인 경우 'False' 으로만 답변해주세요."

        try:
            response_text = generate(video_uri, prompt, facebook_video_data.get('message', ''))
            is_included = response_text.strip() == "True"
            result_message = "포함" if is_included else "미포함"
            
            message = (
                f"**Facebook 영상 업데이트** 📘\n"
                f"영상 제목: {facebook_video_data.get('message', '제목 없음')}\n"
                f"확률형 아이템 문구: {result_message}\n"
                f"영상 URL: {video_uri}\n"
                f"게시물 ID: {facebook_video_data.get('post_id')}\n"
                f"영상 업로드 시간: {facebook_video_data.get('created_time')}"
            )
            send_slack_notification(message)
            return "ok", 200
        except Exception as e:
            logging.error(f"Error processing Facebook webhook: {e}")

    elif is_youtube_webhook:
        logging.info("Detected YouTube webhook.")
        video_data = parse_youtube_webhook_data(data)
        if not video_data:
            logging.warning("Invalid or incomplete YouTube webhook data")
            return

        # 멱등성 키로 사용할 고유 ID (video_id)
        idempotency_key = f"youtube-{video_data['video_id']}"
        if idempotency_key in PROCESSED_EVENTS:
            logging.info(f"Skipping already processed YouTube event: {idempotency_key}")
            return
        PROCESSED_EVENTS.add(idempotency_key)

        video_uri = f"https://www.youtube.com/watch?v={video_data['video_id']}"
        prompt = "다음 YouTube 영상 URI에서 영상의 제목과 설명에 '확률형 아이템 포함' 이라는 문구가 정확히 포함되어 있는지 여부를 판단하여 포함인 경우 'True' 또는 미포함 인 경우 'False' 으로만 답변해주세요."
        
        try:
            response_text = generate(video_uri, prompt, "")
            is_included = response_text.strip() == "True"
            result_message = "포함" if is_included else "미포함"
            
            message = (
                f"**Youtube 영상 업데이트** 📺\n"
                f"영상 제목: {video_data['title']}\n"
                f"확률형 아이템 문구: {result_message}\n"
                f"채널 ID: {video_data['channel_id']}\n"
                f"영상 ID: {video_data['video_id']}\n"
                f"영상 URL: {video_uri}\n"
                f"영상 업로드 시간: {video_data['published']}"
            )
            send_slack_notification(message)
            return "ok", 200
        except Exception as e:
            logging.error(f"Error processing YouTube webhook: {e}")
    else:
        logging.warning("Unsupported webhook event received.")