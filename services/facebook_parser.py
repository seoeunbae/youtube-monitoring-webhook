import logging
from datetime import datetime, timezone

def parse_facebook_webhook(data):
    """
    수신된 Facebook Webhook JSON 데이터를 파싱합니다.
    제공된 스크린샷의 구조를 기반으로 합니다.
    """
    try:
        # 데이터 구조를 안전하게 탐색합니다.
        # entry와 changes는 리스트(list) 형태일 수 있습니다.
        change = data['entry'][0]['changes'][0]
        
        # 'feed' 필드에 대한 변경사항이 아니면 처리하지 않습니다.
        if change.get('field') != 'feed':
            return None

        value = change['value']

        # .get() 메소드를 사용하여 키가 없는 경우에도 오류 없이 안전하게 값을 추출합니다.
        post_id = value.get('post_id')
        message = value.get('message', '')  # 메시지가 없는 경우 빈 문자열 반환
        item_type = value.get('item')       # 'photo', 'video', 'status' 등
        media_url = value.get('link')       # 이미지, 비디오 등의 실제 URL
        created_timestamp = value.get('created_time')

        # Unix 타임스탬프를 사람이 읽을 수 있는 시간 포맷으로 변환합니다.
        created_time_str = "N/A"
        if created_timestamp:
            created_time_str = datetime.fromtimestamp(
                created_timestamp, tz=timezone.utc
            ).strftime('%Y-%m-%d %H:%M:%S UTC')

        # 추출한 값들을 딕셔너리 형태로 반환합니다.
        return {
            'post_id': post_id,
            'message': message,
            'item_type': item_type,
            'media_url': media_url,
            'created_time': created_time_str
        }
    except (KeyError, IndexError, TypeError) as e:
        # JSON 구조가 예상과 다르거나 키가 없는 경우 에러를 기록하고 None을 반환합니다.
        logging.error(f"Facebook Webhook 데이터 파싱 오류: {e}")
        return None