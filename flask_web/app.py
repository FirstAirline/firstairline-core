import os
from flask import jsonify
from flask import Flask, render_template, request
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
from datetime import datetime, timedelta
import pytz  # 타임존 처리를 위한 추가 임포트

load_dotenv()
app = Flask(__name__)

def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv("PG_HOST"),
        port=os.getenv("PG_PORT"),
        database=os.getenv("PG_DB"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD"),
        sslmode='require'
    )
    return conn

def wind_dir_to_text_and_deg(degree):
    # degree(실수/정수) → 8방위 텍스트 + 바늘 회전(deg)
    try:
        deg = float(degree)
    except Exception:
        return {"dir_text": "-", "deg": 0}
    dirs = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    ix = int((deg + 22.5) % 360 // 45)
    dir_text = dirs[ix]
    return {"dir_text": dir_text, "deg": deg}

def format_time_hhmm(hhmm):
    """'1425' → '14시 25분', '0935' → '9시 35분'"""
    if not hhmm or len(hhmm) != 4 or not hhmm.isdigit():
        return hhmm or "-"
    h = int(hhmm[:2])
    m = int(hhmm[2:])
    return f"{h}시 {m:02d}분"

def terminal_code_to_text(code):
    """P01, P02 → '제1 터미널', P03 → '제2 터미널'"""
    if code in ("P01", "P02"):
        return "제1 터미널"
    elif code == "P03":
        return "제2 터미널"
    else:
        return code or "-"

def weather_icon(phenom):
    mapping = {
        "맑음": "☀️",
        "구름": "⛅",
        "구름조금": "🌤️",
        "흐림": "☁️",
        "비": "🌧️",
        "눈": "❄️",
        "안개": "☁️",
    }
    for k, v in mapping.items():
        if k in phenom:
            return v
    return "🌈"

@app.route("/", methods=["GET", "POST"])
def index():
    result = []
    error = None
    show_multi = False
    result_arrival = None  # 도착지 정보 딕셔너리

    if request.method == "POST":
        flight_no = request.form.get("flight_no")
        if not flight_no:
            error = "편명을 입력하세요."
        else:
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                query = sql.SQL("""
                    SELECT year, month, day, airline, flightid, airport, airportcode, terminalid, chkinrange, gatenumber, scheduledatetime, estimateddatetime,
                           yoil, himidity, wind, temp, senstemp, wimage, remark
                    FROM silver.api_silver_departure_weather
                    WHERE flightid = %s
                    ORDER BY timestamp DESC
                    LIMIT 1
                """)
                cur.execute(query, (flight_no,))
                row = cur.fetchone()
                cur.close()
                conn.close()
                if row:
                    # 표(1행)
                    composed = (
                        f"{row[0]}-{row[1]}-{row[2]}",
                        row[3],
                        row[4],
                        f"{row[5]}({row[6]})",
                        terminal_code_to_text(row[7]),
                        row[8],
                        row[9],
                        format_time_hhmm(row[10]),
                        format_time_hhmm(row[11]),
                    )
                    result = [composed]
                    show_multi = False

                    ymd = f"{row[0]}{row[1]}{row[2]}"
                    sched_hhmm = row[10]  # scheduledatetime (예: '1425')
                    terminalid = row[7]   # 'P01', 'P02', 'P03'
                    terminal_short = None
                    if terminalid in ("P01", "P02"):
                        terminal_short = "T1"
                    elif terminalid == "P03":
                        terminal_short = "T2"
                    # 출발예정시간 기준 1시간 전 (예: '1425'→14)
                    hour = "-"
                    if sched_hhmm and len(sched_hhmm) == 4 and sched_hhmm.isdigit():
                        hour = int(sched_hhmm[:2]) - 1
                        if hour < 0:
                            hour = 23
                        hour = f"{hour:02d}"

                    congestion_level = "-"
                    try:
                        if terminal_short and hour != "-":
                            conn3 = get_db_connection()
                            cur3 = conn3.cursor()
                            cur3.execute("""
                                SELECT today_congestion
                                FROM gold.vw_today_vs_lastweek_congestion
                                WHERE today_date = %s
                                AND hour_of_day = %s
                                AND terminal = %s
                                LIMIT 1
                            """, (ymd, hour, terminal_short))
                            congestion_row = cur3.fetchone()
                            if congestion_row:
                                congestion_level = congestion_row[0]
                            cur3.close()
                            conn3.close()
                    except Exception as e:
                        print("[DEBUG] 혼잡도 쿼리 오류:", e)

                    # (추가) 혼잡도에 따른 추천 도착시간 계산
                    congestion_minutes = 60
                    if congestion_level == "여유":
                        congestion_minutes = 60
                    elif congestion_level == "보통":
                        congestion_minutes = 90
                    elif congestion_level in ("혼잡", "매우 혼잡"):
                        congestion_minutes = 120

                    # 출발예정시간 → 추천 도착시간
                    rec_arrival_time = "-"
                    if sched_hhmm and len(sched_hhmm) == 4 and sched_hhmm.isdigit():
                        sh = int(sched_hhmm[:2])
                        sm = int(sched_hhmm[2:])
                        total = sh * 60 + sm - congestion_minutes
                        if total < 0:
                            total += 24 * 60
                        rec_h = total // 60
                        rec_m = total % 60
                        rec_arrival_time = f"{rec_h:02d}:{rec_m:02d}"
                    else:
                        rec_arrival_time = "-"

                    # [혼잡도 결과는 렌더에 같이 전달, None/에러는 '-'로]
                    congestion_info = {
                        "terminal": terminal_short or "-",
                        "level": congestion_level or "-",
                        "hour": hour
                    }

                    # ========== [여기서부터 지연예상시간 쿼리 추가] ==========

                    # (1) 날짜, 편명, 출발예정시간(HH:MM) 포맷 변환
                    sch_time_colon = "-"
                    if sched_hhmm and len(sched_hhmm) == 4 and sched_hhmm.isdigit():
                        sch_time_colon = f"{sched_hhmm[:2]}:{sched_hhmm[2:]}"
                    date_dash = f"{row[0]}-{row[1]}-{row[2]}"
                    expected_delay_val = "-"

                    try:
                        conn4 = get_db_connection()
                        cur4 = conn4.cursor()
                        cur4.execute("""
                            SELECT expected_delay
                            FROM gold.df_final_predic
                            WHERE date = %s
                            AND flight_number = %s
                            AND scheduled_time = %s
                            ORDER BY expected_delay DESC
                            LIMIT 1
                        """, (date_dash, row[4], sch_time_colon))
                        delay_row = cur4.fetchone()
                        if delay_row:
                            expected_delay_val = delay_row[0]
                        cur4.close()
                        conn4.close()
                    except Exception as e:
                        print("[DEBUG] 지연예상시간 쿼리 오류:", e)

                    # ==========================================================

                    # ====== [여기부터 도착지 현지시간, 도시명, 시차 연동 추가] ======
                    arrival_city_time = "-"
                    arrival_city_name = "-"
                    arrival_time_diff = "-"
                    try:
                        airport_code = row[6]  # IATA 코드 (ex: LAX, HND)
                        print("[DEBUG] 도착지 IATA코드:", airport_code)
                        conn2 = get_db_connection()
                        cur2 = conn2.cursor()
                        cur2.execute("""
                            SELECT ko_city, time_diff FROM silver.silver_code_time_diff
                            WHERE iata_code = %s
                            LIMIT 1
                        """, (airport_code,))
                        city_row = cur2.fetchone()
                        cur2.close()
                        conn2.close()
                        if city_row:
                            arrival_city_name = city_row[0]
                            time_diff = city_row[1]
                            print("[DEBUG] 도착도시명:", arrival_city_name, "시차:", time_diff)
                            # 한국 현재시간을 현지시간으로 변환
                            now_kst = datetime.now()  # KST (웹 서버 한국시간 기준)
                            try:
                                local_time = now_kst + timedelta(hours=float(time_diff))
                                yoil_map = ['월','화','수','목','금','토','일']
                                local_md = f"{local_time.month}/{local_time.day}"
                                local_h = local_time.strftime("%H")
                                local_m = local_time.strftime("%M")
                                # 요일(한국 기준 월요일=0, Python: 월0~일6 → +1, %w로 일0~토6, 일-월순서)
                                local_yoil = yoil_map[local_time.weekday()]
                                arrival_city_time = f"{local_md}({local_yoil}) {int(local_h)}시 {int(local_m)}분 (시차: {int(time_diff) if time_diff==int(time_diff) else time_diff}시간)"
                                arrival_time_diff = time_diff
                            except Exception as e:
                                print("[DEBUG] 현지시간 변환 오류:", e)
                                arrival_city_time = "-"
                        else:
                            print("[DEBUG] 도착지 시차 데이터 없음")
                    except Exception as e:
                        print("[DEBUG] 도착지 시간/시차 쿼리 오류:", e)
                        arrival_city_time = "-"

                    # 도착지 추가 정보 (박스)
                    result_arrival = {
                        "yoil": row[12],
                        "himidity": row[13],
                        "wind": row[14],
                        "temp": row[15],
                        "senstemp": row[16],
                        "wimage": row[17],
                        "remark": row[18],
                        # ====== [추가] ======
                        "arrival_city_name": arrival_city_name,
                        "arrival_city_time": arrival_city_time,
                        "arrival_time_diff": arrival_time_diff
                    }
                else:
                    result = []
                    result_arrival = None
                    error = "조회된 데이터가 없습니다."
            except Exception as e:
                error = "DB 조회 중 오류: " + str(e)
                result_arrival = None
    else:
        try:
            page = int(request.args.get('page', 1))
            page_size = 10
            offset = (page - 1) * page_size
            conn = get_db_connection()
            cur = conn.cursor()
            now = datetime.now()
            today = now.date()
            now_time = now.strftime('%H:%M')
            result = []
            total_count = 0

            # 메인 리스트: 20개씩 페이징 (오늘 ~ 7일후 순차 검색)
            for i in range(0, 8):
                target_date = today + timedelta(days=i)
                y, m, d = target_date.strftime("%Y"), target_date.strftime("%m"), target_date.strftime("%d")
                if i == 0:
                    cur.execute("""
                        SELECT * FROM (
                            SELECT year, month, day, airline, flightid, airport, airportcode, terminalid, chkinrange, gatenumber, scheduledatetime, estimateddatetime,
                                ROW_NUMBER() OVER (PARTITION BY flightid, year, month, day ORDER BY timestamp DESC) as rn
                            FROM silver.api_silver_departure_weather
                            WHERE year = %s AND month = %s AND day = %s AND scheduledatetime >= %s
                        ) t
                        WHERE rn = 1
                        ORDER BY year, month, day, scheduledatetime ASC
                        LIMIT %s OFFSET %s
                    """, (y, m, d, now_time.replace(":", ""), page_size, offset))
                else:
                    cur.execute("""
                        SELECT year, month, day, airline, flightid, airport, airportcode, terminalid, chkinrange, gatenumber, scheduledatetime, estimateddatetime
                        FROM silver.api_silver_departure_weather
                        WHERE year = %s AND month = %s AND day = %s
                        ORDER BY year, month, day, scheduledatetime ASC
                        LIMIT %s OFFSET %s
                    """, (y, m, d, page_size, offset))
                rows = cur.fetchall()
                for row in rows:
                    composed = (
                        f"{row[0]}-{row[1]}-{row[2]}",
                        row[3],
                        row[4],
                        f"{row[5]}({row[6]})",
                        terminal_code_to_text(row[7]),
                        row[8],
                        row[9],
                        format_time_hhmm(row[10]),
                        format_time_hhmm(row[11]),
                    )
                    result.append(composed)
                total_count += len(rows)
                if total_count >= page_size:
                    break
            show_multi = True if len(result) > 1 else False
            cur.close()
            conn.close()
            result_arrival = None
        except Exception as e:
            error = "초기 데이터 조회 중 오류: " + str(e)
            result_arrival = None

    weather_list = []
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # **신규 테이블/칼럼 기준 쿼리**
        cur.execute("""
            SELECT observ_date, temperature, dew_point_temperature, qnh,
                mean_wind_speed, max_wind_speed, mean_wind_direction, weather_label
            FROM gold.api_gold_area_weather_data
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        rows = cur.fetchall()
        print('>>> weather rows:', rows)
        for row in rows:
            wind_info = wind_dir_to_text_and_deg(row[6])
            w = {
                "observe_date": row[0],                        # 관측날짜 (ex: "2025-07-16")
                "temperature": row[1],                         # 기온(℃)
                "dew_point_temperature": row[2],               # 이슬점온도(℃)
                "qnh": row[3],                                 # 기압(hPa)
                "mean_wind_speed": row[4],                     # 평균풍속(kt)
                "max_wind_speed": row[5],                      # 최대풍속(kt)
                "mean_wind_direction": wind_info["deg"],       # 풍향(각도)
                "mean_wind_dir_text": wind_info["dir_text"],   # 풍향(텍스트)
                "weather_label": row[7]                        # 날씨라벨(맑음/흐림 등)
            }
            weather_list.append(w)
        cur.close()
        conn.close()
    except Exception as e:
        print('>>> weather error:', e) 
        weather_list = []

    t_air_list = []
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT "terminalid", "total_indoorair_quality_label"
            FROM gold.api_gold_indoorair_quality
            WHERE "terminalid" IN ('T1', 'T2')
            ORDER BY "terminalid"
        """)
        rows = cur.fetchall()
        print(">>>> rows:", rows)
        # 결과는 [(T1, '보통'), (T2, '좋음')] 형식
        for row in rows:
            t_air_list.append({
                "terminalid": row[0],
                "total_label": row[1]
            })
        print(">>>> t_air_list:", t_air_list)
        cur.close()
        conn.close()
    except Exception as e:
        t_air_list = []
        print(">>>> no t_air_list:", t_air_list)

    return render_template(
        "index.html",
        result=result, error=error, show_multi=show_multi,
        weather_list=weather_list,
        weather_icon=weather_icon,
        result_arrival=result_arrival,
        flight_no=flight_no if request.method == "POST" else "",
        page=page if request.method == "GET" else 1,
        t_air_list=t_air_list,
        congestion_info=congestion_info if request.method == "POST" else None,
        expected_delay=expected_delay_val if request.method == "POST" else None,
        rec_arrival_time=rec_arrival_time if request.method == "POST" else None  # ★추가
    )


@app.route("/parking", methods=["GET"])
def parking():
    parking_list = []
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT chargename, chardesc
            FROM gold.parking_test
            ORDER BY 
                CASE 
                    WHEN chargename LIKE '%단기%' THEN 1
                    WHEN chargename LIKE '%장기소형%' THEN 2
                    WHEN chargename LIKE '%장기대형%' THEN 3
                    WHEN chargename LIKE '%화물소형%' THEN 4
                    WHEN chargename LIKE '%화물대형%' THEN 5
                    WHEN chargename LIKE '%프리미엄%' THEN 6
                    WHEN chargename LIKE '%할인%' THEN 7
                    ELSE 99
                END, chargename, chardesc
        """)
        rows = cur.fetchall()
        for row in rows:
            parking_list.append({
                "chargename": row[0],
                "chardesc": row[1]
            })
        cur.close()
        conn.close()
    except Exception as e:
        parking_list = []

    parking_group = {"단기": [], "장기_소형": {}, "장기_대형": {}}
    janggi_daehyung_main = {}
    hwamool_daehyung = {}
    hwamool_daehyung_discount = {}

    for item in parking_list:
        name = item["chargename"]
        desc = item["chardesc"]

        if "무료" in name or "예약" in name or "하우즌" in name:
            continue
        elif "단기" in name and "장기소형" not in name and "장기대형" not in name:
            parking_group["단기"].append(desc)
        elif "장기소형" in name:
            if "장기소형" not in parking_group["장기_소형"]:
                parking_group["장기_소형"]["장기소형"] = []
            parking_group["장기_소형"]["장기소형"].append(desc)
        elif "화물소형" in name:
            if "화물소형" not in parking_group["장기_소형"]:
                parking_group["장기_소형"]["화물소형"] = []
            parking_group["장기_소형"]["화물소형"].append(desc)
        elif "장기대형" in name:
            if "장기대형" not in janggi_daehyung_main:
                janggi_daehyung_main["장기대형"] = []
            janggi_daehyung_main["장기대형"].append(desc)
        elif "주차대형(프리미엄)" in name:
            if "주차대형(프리미엄)" not in janggi_daehyung_main:
                janggi_daehyung_main["주차대형(프리미엄)"] = []
            janggi_daehyung_main["주차대형(프리미엄)"].append(desc)
        elif "화물대형" in name and "할인후" not in name:
            if "화물대형" not in hwamool_daehyung:
                hwamool_daehyung["화물대형"] = []
            hwamool_daehyung["화물대형"].append(desc)
        elif "화물대형할인후" in name:
            if "화물대형할인후" not in hwamool_daehyung_discount:
                hwamool_daehyung_discount["화물대형할인후"] = []
            hwamool_daehyung_discount["화물대형할인후"].append(desc)

    parking_group["장기_대형"].update(janggi_daehyung_main)
    parking_group["장기_대형"].update(hwamool_daehyung)
    parking_group["장기_대형"].update(hwamool_daehyung_discount)

    return render_template("parking.html", parking_group=parking_group)

@app.route("/map")
def map_page():
    return render_template("map.html")

@app.route("/gptchat")
def gptchat_page():
    return render_template("gptchat.html")

@app.route("/restricted")
def restricted_page():
    restricted_list = []
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT category_kr, category_en, image_name, brief,
                   ox_carryon, detail_carryon, ox_checked, detail_checked, detail_common
            FROM gold.restrictedItem
            ORDER BY
                CASE
                    WHEN category_kr = '액체류-화장품·의약품류' THEN 1
                    WHEN category_kr = '액체류-음식물류' THEN 2
                    WHEN category_kr = '위해물품-창·도검류' THEN 3
                    WHEN category_kr = '위해물품-전자충격기·총기·호신용품' THEN 4
                    WHEN category_kr = '위해물품-공구류' THEN 5
                    WHEN category_kr = '위험물-리튬이온배터리' THEN 6
                    WHEN category_kr = '위험물-인화성 가스·방사능' THEN 7
                    ELSE 99
                END
        """)
        rows = cur.fetchall()
        for row in rows:
            restricted_list.append({
                "category_kr": row[0],
                "category_en": row[1],
                "image_name": row[2],
                "brief": row[3],
                "ox_carryon": row[4],
                "detail_carryon": row[5],
                "ox_checked": row[6],
                "detail_checked": row[7],
                "detail_common": row[8]
            })
        cur.close()
        conn.close()
    except Exception as e:
        restricted_list = []

    return render_template("restricted.html", restricted_list=restricted_list)

@app.route('/api/gptchat', methods=['POST'])
def api_gptchat():
    import os
    from openai import AzureOpenAI

    data = request.get_json()
    user_message = data.get('message', '').strip()
    if not user_message:
        return jsonify({'answer': '질문이 입력되지 않았습니다.'})

    # AzureOpenAI 최신 버전(1.x) 방식으로 인증 및 클라이언트 생성
    client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        api_version=os.getenv("AZURE_OPENAI_VERSION"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
    )
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

    chat_prompt = [
        {
            "role": "system",
            "content":
                "너는 인천공항의 실시간 정보를 제공하는 AI 도우미야.\n\n"
                "사용자가 아래와 같은 질문을 하면, 주차 데이터와 터미널 승객 데이터를 종합해서 응답해줘:\n\n"
                "- 지금 어디 주차장이 가장 여유 있어요?\n"
                "- 장기 주차장 중 추천 구역은?\n"
                "- 터미널별 승객이 많은 시간대는 언제인가요?\n"
                "- 현재 터미널1이 혼잡한가요?\n"
                "- 지난주 같은 시간대와 비교해서 더 붐비나요?\n"
                "- 언제 터미널에 도착해야 혼잡시간을 피할 수 있나요?\n\n"
                "출력 조건:\n"
                "- 숫자는 '대' 또는 '명' 단위로 표현\n"
                "- 혼잡도는 그대로 (여유, 보통, 혼잡, 매우 혼잡)\n"
                "- 주차장 정보와 승객 정보 모두 비교/설명할 것\n"
                "- 1~2문장 또는 표로 명확하게 응답\n\n"
                "다음은 실시간 데이터야:\n"
                "[주차장 JSON 데이터 삽입]\n"
                "[터미널별 승객 JSON 데이터 삽입]\n"
        },
        {
            "role": "user",
            "content": user_message
        }
    ]

    try:
        completion = client.chat.completions.create(
            model=deployment,
            messages=chat_prompt,
            max_tokens=800,
            temperature=0.7,
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
        )
        answer = completion.choices[0].message.content.strip() if completion and completion.choices else "답변 생성 실패"
        return jsonify({'answer': answer})
    except Exception as e:
        print("GPT API ERROR:", e)
        return jsonify({'answer': f'에러 발생: {str(e)}'})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
