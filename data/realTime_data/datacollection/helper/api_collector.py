import azure.functions as func
import logging
import requests
import os
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import pytz
from zoneinfo import ZoneInfo
import re

#누림: 인천국제공항공사_기상 정보 API
def get_departure_weather_data():
    url = 'http://apis.data.go.kr/B551177/StatusOfPassengerWorldWeatherInfo/getPassengerDeparturesWorldWeather'
    params = {
        "serviceKey": os.environ.get("nurim_publicdata_api"),
        "numOfRows": "10",
        "pageNo": "1",
        "from_time": "0000",
        "to_time": "2400",
        "flight_id": "",
        "airline": "",
        "lang": "K",
        "type": "json"
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status() # HTTP 요청이 실패했을 경우 requests.exceptions.HTTPError 예외 발생시킴

        logging.info(f"응답 상태코드: {response.status_code}")
        logging.info(f"응답 내용 (text): {response.text[:300]}")  # 처음 300자만 출력

        data = response.json()  
        logging.info(f"API 요청 성공: {data['response']['body']['items'][0]}")
        return data
    
    except requests.exceptions.HTTPError as e:
        logging.error(f"API 요청시 HTTP 오류 발생: {e}")
    except Exception as e:
        logging.error(f"API 요청시 기타 오류 발생: {e}")



#누림: 인천국제공항공사_주차 정보 API
def get_parkinglot_data():
    url = 'http://apis.data.go.kr/B551177/StatusOfParking/getTrackingParking'
    params ={
        'serviceKey' : os.envrion.get("nurim_publicdata_api"),
        'numOfRows' : '100',
        'pageNo' : '1',
        'type' : 'json' }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status() # HTTP 요청이 실패했을 경우 requests.exceptions.HTTPError 예외 발생시킴

        logging.info(f"응답 상태코드: {response.status_code}")
        logging.info(f"응답 내용 (text): {response.text[:300]}")  # 처음 300자만 출력

        data = response.json()  
        logging.info(f"API 요청 성공: {data['response']['body']['items'][0]}")
        return data
    
    except requests.exceptions.HTTPError as e:
        logging.error(f"API 요청시 HTTP 오류 발생: {e}")
    except Exception as e:
        logging.error(f"API 요청시 기타 오류 발생: {e}")



#누림: 인천국제공항공사_실내대기질 정보 API
def get_indoorair_quality_data():
    url = "http://apis.data.go.kr/B551177/IndoorAirQualityInformation/getIndoorAirQs"
    params = {
        'serviceKey': os.environ.get("nurim_publicdata_api"),
        'type': 'json',
        'pageNo': '1',
        'numOfRows': '100'
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status() # HTTP 요청이 실패했을 경우 requests.exceptions.HTTPError 예외 발생시킴

        logging.info(f"응답 상태코드: {response.status_code}")
        logging.info(f"응답 내용 (text): {response.text[:300]}")  # 처음 300자만 출력

        data = response.json()  
        logging.info(f"API 요청 성공: {data['response']['body']['items'][0]}")
        return data
    
    except requests.exceptions.HTTPError as e:
        logging.error(f"API 요청시 HTTP 오류 발생: {e}")
    except Exception as e:
        logging.error(f"API 요청시 기타 오류 발생: {e}")





#승수: 기상청 API
# XML 요소에서 텍스트를 안전하게 추출. 요소가 없으면 기본값을 반환
def safe_get_text(element, path, namespaces, default='-'):
    
    found_element = element.find(path, namespaces)
    return found_element.text if found_element is not None else default

# XML 요소에서 속성을 안전하게 추출. 요소나 속성이 없으면 기본값을 반환
def safe_get_attrib(element, path, namespaces, attrib, default='-'):
    
    found_element = element.find(path, namespaces)
    return found_element.attrib.get(attrib) if found_element is not None else default

# 기상청 API에서 공항 기상 데이터를 조회하는 함수
def get_area_weather_data(pageNo, numOfRows):

    # 기상청 API URL
    url = 'https://apihub.kma.go.kr/api/typ02/openApi/AmmIwxxmService/getMetar'
    
    # API 요청에 필요한 파라미터 설정
    params = {
        'authKey': os.environ.get('kma_api'), 
        'pageNo': str(pageNo), 
        'numOfRows': str(numOfRows), 
        'dataType': 'JSON', 
        'icao': 'RKSI' # 인천국제공항 ICAO 코드
    }

    # API 요청 및 응답 받기
    response = requests.get(url, params=params)
    response.raise_for_status() # 요청 실패 시 예외 발생

    # JSON 파싱
    raw_data = response.content
    json_data = raw_data.decode('utf-8')
    data = json.loads(json_data)

    # 응답 데이터 구조 확인
    items = data.get('response', {}).get('body', {}).get('items', {}).get('item')
    if not items:
        logging.warning("API 응답에서 'item'을 찾을 수 없습니다.")
        return None

    # XML 추출
    xml_string = items[0]['metarMsg']

    # XML 네임스페이스 정의
    namespaces = {
        'iwxxm': 'http://icao.int/iwxxm/2.0',
        'om': 'http://www.opengis.net/om/2.0',
        'gml': 'http://www.opengis.net/gml/3.2',
        'aixm': 'http://www.aixm.aero/schema/5.1.1',
        'sams': 'http://www.opengis.net/samplingSpatial/2.0',
        'sf': 'http://www.opengis.net/sampling/2.0'
    }

    # XML 파싱
    root = ET.fromstring(xml_string)

    # timestamp_now 생성  
    utc_now = datetime.now(tz=timezone.utc)
    kst_now = utc_now.astimezone(pytz.timezone("Asia/Seoul"))
    timestamp_now = kst_now.strftime("%Y-%m-%d %H:%M:%S")

    # 관측 시간 추출 후 변환
    utc_dt = datetime.fromisoformat(root.find('.//gml:timePosition', namespaces).text.replace('Z', '+00:00'))
    kst_dt = utc_dt.astimezone(ZoneInfo("Asia/Seoul"))
    date_str = kst_dt.strftime('%Y%m%d')
    time_str = kst_dt.strftime('%H:%M:%S')

    # 바람 정보 추출
    wind_element = root.find('.//iwxxm:AerodromeSurfaceWind', namespaces)

    #구름 정보 추출
    cloud_pattern = re.compile(r'\b(CAVOK|NSC|(?:FEW|SCT|BKN|OVC|VV)\d{3}(?:CB|TCU)?)\b')
    found_clouds = cloud_pattern.findall(root.find('.//iwxxm:extension/msgText', namespaces).text)
    found_clouds = ' '.join(found_clouds) if found_clouds else "No_clouds"

    # 데이터를 저장할 딕셔너리 생성
    metar_data = {
        "date": date_str,  # 데이터 관측 날짜 (한국 시간 기준)
        "time": time_str,  # 데이터 관측 시간 (한국 시간 기준)
        "report_type": "METAR",  # 보고서 종류 (METAR: 정시 항공 기상 관측 보고)
        "raw_text": safe_get_text(root, './/iwxxm:extension/msgText', namespaces, default=""),  # 원본 METAR 전문
        "station_type": "AUTOMATED" if root.attrib.get('automatedStation') == 'true' else "MANNED",  # 관측소 종류 (유인 : MANNED / 무인 : AUTOMATED)
        "status": root.attrib.get('status'),  # 보고서 상태 (예: NORMAL)
        "permissible_usage": root.attrib.get('permissibleUsage'),  # 사용 목적 (예: OPERATIONAL)
        "temperature": safe_get_text(root, './/iwxxm:airTemperature', namespaces),  # 기온 (섭씨)
        "dew_point_temperature": safe_get_text(root, './/iwxxm:dewpointTemperature', namespaces),  # 이슬점 온도 (섭씨)
        "qnh": safe_get_text(root, './/iwxxm:qnh', namespaces),  # 해면 기압 (QNH, 헥토파스칼)
        "mean_wind_speed": safe_get_text(wind_element, 'iwxxm:meanWindSpeed', namespaces),  # 평균 풍속 (노트)
        "max_wind_speed": safe_get_text(wind_element, 'iwxxm:windGustSpeed', namespaces),  # 최대 풍속 (노트)
        "mean_wind_direction": safe_get_text(wind_element, 'iwxxm:meanWindDirection', namespaces),  # 평균 풍향 (도)
        "counter_clock_wind_direction": safe_get_text(wind_element, 'iwxxm:extremeCounterClockwiseWindDirection', namespaces),  # 최소 풍향 (반시계 방향)
        "clock_wind_direction": safe_get_text(wind_element, 'iwxxm:extremeClockwiseWindDirection', namespaces),  # 최대 풍향 (시계 방향)
        "horizontal_visibility": safe_get_text(root, './/iwxxm:prevailingVisibility', namespaces),  # 우시정 (미터 단위)
        "clouds": found_clouds,  # 구름 정보 (이전 단계에서 안전하게 처리됨)
        "change_indicator": safe_get_attrib(root, './/iwxxm:MeteorologicalAerodromeTrendForecastRecord', namespaces, 'changeIndicator')  # 착륙 예보 (향후 2시간 동향), 변화 지시어 (예: NOSIG - 변화 없음)
    }
    
    payload = {
        "source": "api_bronze_area_weather_data",
        "timestamp" :  timestamp_now, # 데이터 수집 시각
        "data" : (metar_data)
    }

    return payload


#상원: 인천국제공항공사_출입국별 승객 예고 정보 API
def get_departure_forecast_data():
    url = 'http://apis.data.go.kr/B551177/PassengerNoticeKR/getfPassengerNoticeIKR'
    params ={'serviceKey' : os.environ.get("sangwon_publicdata_api"), 'selectdate' : '0', 'type' : 'json' }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        logging.info(f"응답 상태코드: {response.status_code}")
        logging.info(f"응답 내용 (text): {response.text[:300]}")
        data = response.json()
        items = data.get('response', {}).get('body', {}).get('items', [])
        if items:
            logging.info(f"API 요청 성공: {items[0]}")
        else:
            logging.warning("API 응답에 items가 없습니다.")
        return data
    except requests.exceptions.HTTPError as e:
        logging.error(f"API 요청시 HTTP 오류 발생: {e}")
    except Exception as e:
        logging.error(f"API 요청시 기타 오류 발생: {e}")
