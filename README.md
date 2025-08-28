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






