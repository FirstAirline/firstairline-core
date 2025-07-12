import os
from flask import Flask, render_template, request
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
from datetime import datetime, timedelta

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

@app.route("/", methods=["GET", "POST"])
def index():
    result = []
    error = None
    show_multi = False

    if request.method == "POST":
        flight_no = request.form.get("flight_no")
        flight_date = request.form.get("flight_date")
        if not flight_no or not flight_date:
            error = "모든 입력값을 채워주세요."
        else:
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                query = sql.SQL("""
                    SELECT 날짜, 연도, 월, 일, 요일코드, 항공사, 편명, 도착지, 계획시간, 출발시간, 지연원인, 지연시간
                    FROM gold.flasktest
                    WHERE 편명 = %s AND 날짜 = %s
                """)
                cur.execute(query, (flight_no, flight_date))
                row = cur.fetchone()
                cur.close()
                conn.close()
                if row:
                    result = [row]
                    show_multi = True
                else:
                    result = []
                    error = "조회된 데이터가 없습니다."
            except Exception as e:
                error = "DB 조회 중 오류: " + str(e)
    else:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            # 오늘 날짜 구하기 (서버 기준)
            today = datetime.now().date()
            result = []
            # 오늘 데이터 먼저 10개까지 뽑기
            cur.execute("""
                SELECT 날짜, 연도, 월, 일, 요일코드, 항공사, 편명, 도착지, 계획시간, 출발시간, 지연원인, 지연시간
                FROM gold.flasktest
                WHERE 날짜 = %s
                ORDER BY 출발시간 ASC
                LIMIT 10
            """, (today,))
            rows = cur.fetchall()
            result.extend(rows)
            # 만약 10개 미만이면, 다음날(미래) 데이터에서 남은 개수만큼 채우기
            if len(result) < 10:
                # 오늘 이후의 날짜 모두 조회(최대 5일치 정도만 반복)
                additional_needed = 10 - len(result)
                for i in range(1, 8):
                    next_date = today + timedelta(days=i)
                    cur.execute("""
                        SELECT 날짜, 연도, 월, 일, 요일코드, 항공사, 편명, 도착지, 계획시간, 출발시간, 지연원인, 지연시간
                        FROM gold.flasktest
                        WHERE 날짜 = %s
                        ORDER BY 출발시간 ASC
                        LIMIT %s
                    """, (next_date, additional_needed))
                    rows_next = cur.fetchall()
                    if rows_next:
                        result.extend(rows_next)
                        additional_needed = 10 - len(result)
                        if additional_needed <= 0:
                            break
            show_multi = True if result else False
            cur.close()
            conn.close()
        except Exception as e:
            error = "초기 데이터 조회 중 오류: " + str(e)

    return render_template("index.html", result=result, error=error, show_multi=show_multi)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
