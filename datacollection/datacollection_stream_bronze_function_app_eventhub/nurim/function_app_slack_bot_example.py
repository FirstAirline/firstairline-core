import azure.functions as func
import logging
import requests
import os
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import pytz


# FunctionApp 인스턴스를 생성
app = func.FunctionApp()



#누림: 인천국제공항공사_기상 정보 API
@app.timer_trigger(schedule="0 */10 * * * *", arg_name="timer", run_on_startup=True, use_monitor=False)
@app.event_hub_output(arg_name="event", event_hub_name= os.environ["Team1EventHubName"], connection="Team1EventHubConnectionString")
def api_eventhub_departure_weather(timer: func.TimerRequest, event:func.Out[str]) -> None:
    logging.info("API 수집 시작: departure_weather")

    #1. 시간 처리
    utc_now = datetime.now(tz=timezone.utc) #현재UTC시간
    kst_now = utc_now.astimezone(pytz.timezone("Asia/Seoul")) #한국시간
    timestamp_now = kst_now.strftime("%Y-%m-%d %H:%M:%S")

    #2. API 요청
    from helper.api_collector import get_departure_weather_data
    result = get_departure_weather_data()

    #3. Event Hub에 데이터 전송
    if result:
        body = result['response']['body']
        #items = result['response']['body']['items']
        #items_json = json.dumps(items, ensure_ascii=False)
        #items_as_dict = {str(i): item for i, item in enumerate(items)}
        logging.info(f"전체 데이터 전송 준비 완료: {body}")
        payload = {
            "source": "api_bronze_departure_weather",
            "event_timestamp" : timestamp_now,
            "data" : body
        }
        event.set(json.dumps(payload))

    #4. 웹훅요청 (Slack)
    webhook_url = "https://hooks.slack.com/services/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"
    text = f"[알림] {timestamp_now} 기준 departure_weather API 수집 완료.\n 예시 데이터: {body['items'][0]}"

    payload = {
        "text": text,
        "username": "API 알림봇",
        "icon_emoji": ":rocket:"
    }

    response = requests.post(webhook_url, data=json.dumps(payload), headers={"Content-Type": "application/json"})

    if response.status_code == 200:
        logging.info("Slack 전송 성공")
    else:
        logging.info(f"Slack 전송 실패: {response.status_code} / {response.text}")