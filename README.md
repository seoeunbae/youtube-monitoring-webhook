# AI-Powered YouTube Marketing Compliance Monitoring System
Youtube 영상 규정 준수 자동 분석 및 Slack 알림 시스템 입니다.

<br>

## 📝 Overview

이 프로젝트는 지정된 YouTube 채널에 새로운 영상이 업로드될 때, 게임 산업의 광고 심의 및 마케팅 규제에 따라 콘텐츠에 필수로 포함되어야 하는 고지 문구인  "확률형 아이템 포함" 용어가 있는지 Vertex AI를 통해 분석하고, 누락 시 결과를 Slack으로 즉시 알려주는 자동화 시스템입니다.

**서버리스 아키텍처를 기반으로, 수동 검수 과정을 최소화하고 규제 위반 리스크를 사전에 관리할 수 있는 컴플라이언스 모니터링을 지원합니다.**

**금융, 의료, 식품, 게임 등 다양한 산업의 광고 심의 및 마케팅 규제에 재활용될 수 있으며, 개발리소스 없이도 마케팅에서 바로 적용이 가능합니다.**



<br>

## ⚙️ Architectrue

<img width="946" height="498" alt="Image" src="https://github.com/user-attachments/assets/3c357798-432d-430d-bcc3-6338c3ade071" />

<br>

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

<br>

## Project structure 

```
/youtube-webhook
└── services
     ├── gemini.py
     ├── parser.py
     └── slack.py
├── main.py
├── requirements.txt
└── .env
```

<br>


##  How to use

**1. 소스코드 다운로드**

**2. Cloud function 배포:** 작성된 코드를 컨테이너화하여 Cloud Run에 배포합니다.

**3. Slack Webhook 연동 :** Slack webhook URL을 생성하고 연동합니다.

**3. YouTube Hub 구독:** 배포된 Cloud Run 서비스의 URL을 사용하여 특정 YouTube 채널의 업데이트 알림을 구독 신청합니다.
 - https://pubsubhubbub.appspot.com/subscribe

<br>

## ⚙️ Cloud shell Command 

1. clone the code

```
git clone https://github.com/seoeunbae/youtube-monitoring-webhook.git
```

2. set the environment variables

```
export PROJECT_ID=$(gcloud config get-value project)
export REGION="us-central1"
export SERVICE_NAME="{SERVICE_NAME}"
```

3. activate API 

```
gcloud services enable cloudfunctions.googleapis.com aiplatform.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
```

4. deploy Cloud function

```
gcloud run deploy ${SERVICE_NAME} \ 
  --source . \
  --base-image python313 \
  --function youtube_webhook \
  --region ${REGION} \
  --allow-unauthenticated
```

5. set the Slack Webhook

   Slack -> setting -> add Apps -> Incoming webhooks 생성 
<br>

6. subscribe youtube with Pubsubhubhub.com 
- https://pubsubhubbub.appspot.com/subscribe
로 들어가서 아래에 해당하는 값들을 입력 후 subscribe합니다.
 - 1. callback URL = {YOUR_CLOUD_FUNCTION_URL}
 - 2. Topic URL = https://www.youtube.com/xml/feeds/videos.xml?channel_id={YOUR_CHANNEL_ID} 






