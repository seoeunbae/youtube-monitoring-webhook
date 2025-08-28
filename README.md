# YouTube 영상 규정 준수 자동 분석 및 Slack 알림 시스템

## 📝 프로젝트 개요

이 프로젝트는 지정된 YouTube 채널에 새로운 영상이 업로드될 때, 해당 영상에 법적으로 명시해야 하는 특정 용어가 포함되었는지 자동으로 분석하고 결과를 Slack으로 즉시 알려주는 자동화 시스템입니다.

서버리스 아키텍처를 기반으로 구축되어 효율적이고 신속하게 영상의 규정 준수 여부를 모니터링할 수 있습니다

---

## ⚙️ Architectrue

<img width="1388" height="740" alt="Image" src="https://github.com/user-attachments/assets/05f03c44-b8bb-4165-aa51-a7e056362efe" />

## Project structure 

```
/youtube-webhook
├── main.py
├── requirements.txt
└── .env
```

## Architecture Flow

**1. YouTube Push Notifications 설정:**
  YouTube Data API를 사용하여 특정 채널에 새 동영상이 업로드될 때마다 알림을 받을 Pub/Sub 토픽을 구독. 

**2. Cloud Function (1) - 콘텐츠 분석 트리거:**
  트리거: 위에서 설정한 Pub/Sub 토픽에 메시지가 도착하면 이 함수가 자동으로 실행.
    역할: Pub/Sub 메시지에서 새로 업로드된 동영상 ID를 추출.
    - 1. YouTube Data API를 호출하여 동영상의 기본 정보(제목, 설명)와 자막(Caption) 데이터를 가져옴.
    - 2. 추출한 모든 텍스트 데이터(제목, 설명, 자막)와 동영상 파일을 분석할 수 있도록 Vertex AI Gemini API를 호출.

**3. Vertex AI (Gemini 2.5 Pro or Flash):**
  역할: 멀티모달(Multimodal) 기능을 활용하여 콘텐츠를 종합적으로 분석.
    분석 내용:
      - 1. 영상 분석: Cloud Function에서 전달받은 영상 컨텐츠에 '확률형 아이템 포함' 문구가 있는지 확인.
      - 2. 이미지 분석 (OCR): YouTube 커뮤니티 탭 등에 이미지가 게시될 경우, 해당 이미지 내 텍스트를 인식하여 문구를 확인.
    결과: 분석 후 '확률형 아이템 포함' 문구의 존재 여부를 Boolean형태로 반환.

**4. Cloud Function (2) - 알림 발송:**
  트리거: Vertex AI 분석이 완료된 후, 첫 번째 Cloud Function이 결과에 따라 이 함수를 호출하거나 또는 별도의 Pub/Sub 토픽으로 결과를 전달하여 트리거.
  - 역할:
    Gemini의 분석 결과가 false일 경우, Slack Webhook API 호출.
    Slack 메시지에 어떤 동영상에서 문구가 누락되었는지 식별할 수 있도록 동영상 링크와 제목을 포함하여 알림을 보냄.


---


## ✅  구현 시나리오

전체적인 흐름은 다음과 같습니다.
**1. 소스코드 작성**

**2. Cloud function 배포:** 작성한 코드를 컨테이너화하여 Cloud Run에 배포합니다.

**3. Slack Webhook 연동 :** Slack webhook URL을 생성하고 연동합니다.

**3. YouTube Hub 구독:** 배포된 Cloud Run 서비스의 URL을 사용하여 특정 YouTube 채널의 업데이트 알림을 구독 신청합니다.
 - https://pubsubhubbub.appspot.com/subscribe

## ⚙️ Cloud shell에서 사용하는 법

1. 소스 코드 다운로드

```
git clone https://github.com/seoeunbae/youtube-monitoring-webhook.git
```

2. 환경 변수 설정

```
export PROJECT_ID=$(gcloud config get-value project)
export REGION="us-central1"
export SERVICE_NAME="{SERVICE_NAME}"
```

3. API 활성화 

```
gcloud services enable cloudfunctions.googleapis.com aiplatform.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
```

4. Cloud functions에 배포합니다.

```
gcloud run deploy ${SERVICE_NAME} \ 
  --source . \
  --base-image python313 \
  --function youtube_webhook \
  --region ${REGION} \
  --allow-unauthenticated
```

5. Slack 연동

   Slack -> setting -> add Apps -> Incoming webhooks 생성 

6. Pubsubhubhub 
- https://pubsubhubbub.appspot.com/subscribe
로 들어가서 아래에 해당하는 값들을 입력 후 subscribe합니다.
 - 1. callback URL = {YOUR_CLOUD_FUNCTION_URL}
 - 2. Topic URL = https://www.youtube.com/xml/feeds/videos.xml?channel_id={YOUR_CHANNEL_ID} 






