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


#누림: 인천국제공항공사_주차 정보 API
@app.timer_trigger(schedule="0 */5 * * * *", arg_name="timer", run_on_startup=True, use_monitor=False)
@app.event_hub_output(arg_name="event", event_hub_name= os.environ["Team1EventHubName"], connection="Team1EventHubConnectionString")
def api_eventhub_parkinglot(timer: func.TimerRequest, event:func.Out[str]) -> None:
    logging.info("API 수집 시작: parkinglot")

    #1. 시간 처리
    utc_now = datetime.now(tz=timezone.utc) #현재UTC시간
    kst_now = utc_now.astimezone(pytz.timezone("Asia/Seoul")) #한국시간
    timestamp_now = kst_now.strftime("%Y-%m-%d %H:%M:%S")

    #2. API 요청
    from helper.api_collector import get_parkinglot_data
    result = get_parkinglot_data()

    #3. Event Hub에 데이터 전송
    if result:
        body = result['response']['body']
        logging.info(f"데이터 전송 준비 완료: {body}")
        payload = {
            "source": "api_bronze_parkinglot",
            "timestamp": timestamp_now,
            "data": body 
        }
        event.set(json.dumps(payload))


#누림: 인천국제공항공사_실내대기질 정보 API
@app.timer_trigger(schedule="0 0 * * * *", arg_name="timer", run_on_startup=True, use_monitor=False)
@app.event_hub_output(arg_name="event", event_hub_name= os.environ["Team1EventHubName"], connection="Team1EventHubConnectionString")
def api_eventhub_indoorair_quality(timer: func.TimerRequest, event:func.Out[str]) -> None:
    logging.info("API 수집 시작: indoorair_quality")

    #1. 시간 처리
    utc_now = datetime.now(tz=timezone.utc) #현재UTC시간
    kst_now = utc_now.astimezone(pytz.timezone("Asia/Seoul")) #한국시간
    timestamp_now = kst_now.strftime("%Y-%m-%d %H:%M:%S")

    #2. API 요청
    from helper.api_collector import get_indoorair_quality_data
    result = get_indoorair_quality_data()

    #3. Event Hub에 데이터 전송
    if result:
        body = result['response']['body']
        logging.info(f"데이터 전송 준비 완료: {body}")
        payload = {
            "source": "api_bronze_indoorair_quality",
            "timestamp": timestamp_now,
            "data": body 
        }
        event.set(json.dumps(payload))


#승수: 기상청 API
# time trigger 부분
# @app.timer_trigger 데코레이터를 사용하여 시간 트리거 함수를 정의합니다.
@app.timer_trigger(schedule="0 1,11,21,31,41,51 * * * *", arg_name="timer", run_on_startup=True, use_monitor=False)
@app.event_hub_output(arg_name="event", event_hub_name= os.environ["Team1EventHubName"], connection="Team1EventHubConnectionString")
def timer_trigger_weather(timer: func.TimerRequest, event: func.Out[str]) -> None:

    utc_timestamp = datetime.now(timezone.utc).isoformat()

    try:
        logging.info("기상 데이터 조회를 시작합니다. %s", utc_timestamp)
        # 페이지 번호 1, 행 수 10으로 데이터 조회 함수 호출
        from helper.api_collector import get_area_weather_data
        weather_info = get_area_weather_data(pageNo=1, numOfRows=10)

        event.set(json.dumps(weather_info))

        if weather_info:
            # 조회된 데이터를 보기 좋게 로깅합니다.
            logging.info("=== 조회된 기상 정보 ===")
            for key, value in weather_info.items():
                logging.info(f"{key}: {value}")
            logging.info("=======================")
        else:
            logging.warning("조회된 기상 정보가 없습니다.")

    # 발생한 오류 처리
    except requests.exceptions.RequestException as e:
        logging.error(f"API 요청 중 오류가 발생했습니다: {e}")
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logging.error(f"데이터 파싱 중 오류가 발생했습니다: {e}")
    except ET.ParseError as e:
        logging.error(f"XML 파싱 중 오류가 발생했습니다: {e}")
    except Exception as e:
        logging.error(f"알 수 없는 오류가 발생했습니다: {e}", exc_info=True)

    logging.info('기상 데이터 조회를 완료했습니다.')




#상원: 인천국제공항공사_출입국별 승객 예고 정보 API
#@app.timer_trigger(schedule="0 */5 * * * *", arg_name="timer", run_on_startup=True, use_monitor=False) 이거 5분
@app.timer_trigger(schedule="0 10 17 * * *", arg_name="timer", run_on_startup=True, use_monitor=False) # 이건 17시 10분에 하루한번
@app.event_hub_output(arg_name="event", event_hub_name= os.environ["Team1EventHubName"], connection="Team1EventHubConnectionString")
def api_eventhub_departure_forecast(timer: func.TimerRequest, event:func.Out[str]) -> None:
    logging.info("API 수집 시작: _departure_forecast")

    utc_now = datetime.now(tz=timezone.utc)
    kst_now = utc_now.astimezone(pytz.timezone("Asia/Seoul"))
    timestamp_now = kst_now.strftime("%Y-%m-%d %H:%M:%S")

    from helper.api_collector import get_departure_forecast_data
    result = get_departure_forecast_data()
    items = result.get('response', {}).get('body', {}).get('items', []) if result else []

    if items:
        body = result['response']['body']
        items_as_dict = {str(i): item for i, item in enumerate(items)} # 배열 → 딕셔너리
        logging.info(f"데이터 전송 준비 완료: {body}")
        payload = {
            "source": "api_bronze_departure_forecast",
            "timestamp": timestamp_now,
            "data": body
        }
        event.set(json.dumps(payload))
        text = f"[알림] {timestamp_now} 기준 departure_forecast API 수집 완료.\n 예시 데이터: {body}"
    else:
        text = f"[경고] {timestamp_now} 기준 departure_forecast API 응답에 데이터가 없습니다."