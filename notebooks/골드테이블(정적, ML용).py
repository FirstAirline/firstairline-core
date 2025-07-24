# Databricks notebook source
from pyspark.sql.functions import when, col, lpad, count, substring, concat, to_date, lit, format_number, round, sum as _sum
from pyspark.sql import functions as F

# COMMAND ----------

# 1. 메인테이블 불러오기 - 시간대컬럼 추출
df_flight = spark.table("`1team-postgresql-connection_catalog`.silver.silver_flight_info")
# day_of_week Column
# 1 = 일요일
# 2 = 월요일
# 3 = 화요일
# 4 = 수요일
# 5 = 목요일
# 6 = 금요일
# 7 = 토요일

df_flight.display()

# COMMAND ----------

# 2. 계획시간, 출발시간의 시간부분 추출, 지연 시간 열 추가 (취소건은 null)
df_flight = df_flight.withColumn(
    "scheduled_hour",
    substring("scheduled_time", 1, 2)
).withColumn(
    "departure_hour",
    when(
        (col("departure_time").isNotNull()) & 
        (col("departure_time") != '') & 
        (col("departure_time") != ':'),
        substring("departure_time", 1, 2)
    ).otherwise(None)
).withColumn(
    "delayed_time",
    when(col("delayed_time") == "취소", None)
    .otherwise(col("delayed_time"))
)

df_flight = df_flight.withColumn(
    "month",
    lpad(col("month"), 2, "0")
)

df_flight.display()

# COMMAND ----------

# 3. 날짜 형식 변환(yyyy-mm-dd) & 평일(0)/주말(1) 컬럼 추가
df_flight = df_flight.withColumn(
    "date",
    col("date").cast("string")  
).withColumn(
    "date",
    concat(
        substring("date", 1, 4), lit("-"),
        substring("date", 5, 2), lit("-"),
        substring("date", 7, 2)
    )
)

df_flight.display()

# COMMAND ----------

# 4.시간대별, 월별, 요일별, 항공사별 테이블 불러오기
df_hourly = spark.table("`1team-postgresql-connection_catalog`.silver.silver_hourly")
df_monthly = spark.table("`1team-postgresql-connection_catalog`.silver.silver_monthly")
df_weekday = spark.table("`1team-postgresql-connection_catalog`.silver.silver_weekday")
df_airline = spark.table("`1team-postgresql-connection_catalog`.silver.silver_airline")

df_hourly.display()
df_monthly.display()
df_weekday.display()
df_airline.display()

# COMMAND ----------

# 5. month 컬럼 0 추가
df_hourly = df_hourly.withColumn(
    "month",
    lpad(col("month"), 2, "0")
)
df_monthly = df_monthly.withColumn(
    "month",
    lpad(col("month"), 2, "0")
)
# 1. 월별로 총합 집계
monthly_sum = df_monthly.groupBy("year", "month").agg(
    _sum("passenger_departure").alias("monthly_passenger_total"),
    _sum("cargo_departure").alias("monthly_cargo_total"),
    _sum("flight_departure").alias("monthly_flight_total")
)

# 2. 원본 df_monthly와 월별 year, month로 조인
df_monthly = df_monthly.join(
    monthly_sum,
    on=["year", "month"],
    how="left"
)

df_hourly.display()
df_monthly.display()

# COMMAND ----------

# 6. 항공사별 테이블에 존재하는 항공사만 남기기
df_flight_filtered = df_flight.join(
    df_airline.select("airline").distinct(),
    "airline",
    "inner"
)

df_flight_filtered.display()

# COMMAND ----------

df_flight_filtered.count()

# COMMAND ----------

# 7. 메인 테이블에서 취소된 데이터 제외
df_valid = df_flight_filtered.filter(
    (col("departure_time") != ":") & (col("status") != "취소")
)

df_valid.display()

# COMMAND ----------

df_valid.count()

# COMMAND ----------

# 8. 항공사별 테이블의 월별 총합 계산
airline_sum = df_airline.groupBy("year", "month").agg(
    _sum("flight_departures").alias("airline_flight_departure_sum"),
    _sum("passenger_departures").alias("airline_passenger_departure_sum"),
    _sum("cargo_departures").alias("airline_cargo_departure_sum")
)

airline_sum.display()

# COMMAND ----------

# 9. 항공사별 테이블의 비율 계산
airline_ratio = df_airline.join(
    airline_sum, on=["year", "month"]
).withColumn(
    "a_flight_ratio", col("flight_departures") / col("airline_flight_departure_sum")
).withColumn(
    "a_passenger_ratio", col("passenger_departures") / col("airline_passenger_departure_sum")
).withColumn(
    "a_cargo_ratio", col("cargo_departures") / col("airline_cargo_departure_sum")
)

airline_ratio.display()

# COMMAND ----------

# 10. 시간대별 테이블의 월별 총합 계산
hourly_sum = df_hourly.groupBy("year", "month").agg(
    _sum("flight_departure").alias("hourly_flight_departure"),
    _sum("passenger_departure").alias("hourly_passenger_departure"),
    _sum("cargo_departure").alias("hourly_cargo_departure")
)

hourly_sum.display()

# COMMAND ----------

# 11. 시간대별 테이블의 비율 계산
time_ratio = df_hourly.join(
    hourly_sum, on=["year", "month"]
).withColumn(
    "t_flight_ratio", col("flight_departure") / col("hourly_flight_departure")
).withColumn(
    "t_passenger_ratio", col("passenger_departure") / col("hourly_passenger_departure")
).withColumn(
    "t_cargo_ratio", col("cargo_departure") / col("hourly_cargo_departure")
)

time_ratio.display()

# COMMAND ----------

# 12. 메인 테이블의 비행 데이터를 활용한 일자별, 월별 합계 및 비율 계산
day_total = df_valid.groupBy("year", "month", "day").count().withColumnRenamed("count", "flight_day_total")
month_total = df_valid.groupBy("year", "month").count().withColumnRenamed("count", "flight_month_total")

day_ratio = day_total.join(month_total, on=["year", "month"]).withColumn(
    "day_ratio", col("flight_day_total") / col("flight_month_total")
).orderBy(
        col("year").cast("int").asc(),
        col("month").cast("int").asc(),
        col("day").cast("int").asc())

day_ratio.display()

# COMMAND ----------

# # 16. 날짜/시간대/항공사별 실제 운항편수
# actual_flight_count = airline_stat.select(
#     "year", "month", "day", "scheduled_hour", "airline", col("flight_total_airline").alias("actual_flight_count")
# )

# actual_flight_count.display()

# COMMAND ----------

# 13. 컬럼명 간소화
ar = airline_ratio.alias("ar")
dr = day_ratio.alias("dr")
tr = time_ratio.alias("tr")
dm = df_monthly.alias("dm")
df = df_valid.alias("df")

# COMMAND ----------

# 14. 모든 비율 조인
df_joined = df \
    .join(dr, (col("df.year") == col("dr.year")) & (col("df.month") == col("dr.month")) & (col("df.day") == col("dr.day")), "left") \
    .join(tr, (col("df.year") == col("tr.year")) & (col("df.month") == col("tr.month")) & (col("df.scheduled_hour") == col("tr.hour_of_day")), "left") \
    .join(dm, (col("df.year") == col("dm.year")) & (col("df.month") == col("dm.month")), "left") \
    .join(ar, (col("df.year") == col("ar.year")) & (col("df.month") == col("ar.month")) & (col("df.airline") == col("ar.airline")), "left")

df_selected = df_joined.select(
    col("df.year").alias("year"),
    col("df.month").alias("month"),
    col("df.airline").alias("airline"),
    col("df.date").alias("date"),
    col("df.day").alias("day"),
    col("df.day_of_week").alias("day_of_week"),
    col("df.flight_number").alias("flight_number"),
    col("df.destination_city").alias("destination_city"),
    col("df.scheduled_time").alias("scheduled_time"),
    col("df.departure_time").alias("departure_time"),
    col("df.flight_type").alias("flight_type"),
    col("df.status").alias("status"),
    col("df.is_departed").alias("is_departed"),
    col("df.delay_reason").alias("delay_reason"),
    col("df.delayed_time").alias("delayed_time"),
    col("df.scheduled_hour").alias("scheduled_hour"),
    col("df.departure_hour").alias("departure_hour"),
    col("dr.day_ratio").alias("day_ratio"),
    col("tr.t_flight_ratio").alias("t_flight_ratio"),
    col("tr.t_passenger_ratio").alias("t_passenger_ratio"),
    col("tr.t_cargo_ratio").alias("t_cargo_ratio"),
    col("ar.a_flight_ratio").alias("a_flight_ratio"),
    col("ar.a_passenger_ratio").alias("a_passenger_ratio"),
    col("ar.a_cargo_ratio").alias("a_cargo_ratio"),
    col("dm.flight_departure").alias("flight_departure"),
    col("dm.passenger_departure").alias("passenger_departure"),
    col("dm.cargo_departure").alias("cargo_departure"),
    col("dm.monthly_passenger_total").alias("monthly_passenger_total"),
    col("dm.monthly_cargo_total").alias("monthly_cargo_total"),
    col("dm.monthly_flight_total").alias("monthly_flight_total")
)
df_selected.display()

# COMMAND ----------

# 19. 추정치 계산(총합 * 비율 * 비율 * 비율)
df_estimated = df_selected.withColumn(
    "expected_passenger",
    col("passenger_departure") * col("day_ratio") * col("t_passenger_ratio") * col("a_passenger_ratio")
).withColumn(
    "expected_cargo",
    col("cargo_departure") * col("day_ratio") * col("t_cargo_ratio") * col("a_cargo_ratio")
)

df_estimated.display()

# COMMAND ----------

# 22. 월별 추정치 합계 계산
estimated_sum_df = df_estimated.groupBy("year", "month").agg(
    _sum("expected_passenger").alias("total_estimated_passenger"),
    _sum("expected_cargo").alias("total_estimated_cargo")
)

estimated_sum_df.display()

# COMMAND ----------

# 월별 보정계수 계산
scaling_df = (
    estimated_sum_df
    .join(dm, on=["year", "month"])
    .withColumn("scaling_passenger", col("dm.monthly_passenger_total") / col("total_estimated_passenger"))
    .withColumn("scaling_cargo",  col("dm.monthly_cargo_total") / col("total_estimated_cargo"))
)

scaling_df = scaling_df.drop("date", "day")

scaling_df.display()

# COMMAND ----------

df_final = (
    df_estimated
    .join(scaling_df, on=["year", "month"], how="left")
    .withColumn("final_est_passenger", col("expected_passenger") * col("scaling_passenger"))
    .withColumn("final_est_cargo", col("expected_cargo") * col("scaling_cargo"))
)

df_final.display()

# COMMAND ----------

df_final.count()

# COMMAND ----------

df_final.agg(
    _sum("final_est_passenger").alias("total_estimated_passenger"),
    _sum("final_est_cargo").alias("total_estimated_cargo")).display()

# COMMAND ----------

# 23. 실제 값과 추정치 비교(2)
dm.agg(
    _sum("passenger_departure").alias("total_passenger"),
    _sum("cargo_departure").alias("total_cargo")
).show()

# COMMAND ----------

# 21. 사용할 컬럼 추출 및 메인 테이블과 조인
df_final2 = df_final.select(
    "date", "year", "month", "day", "airline", "day_of_week", "flight_number", "destination_city", "scheduled_time", "departure_time", "flight_type", "status", "scheduled_hour", "departure_hour", "is_departed", "delayed_time", "delay_reason", "final_est_passenger", "final_est_cargo"
)
df_final2 = df_final2.withColumn(
    "day",
    lpad(col("day"), 2, "0")
)

df_final2.display()

# COMMAND ----------

df_final2.count()

# COMMAND ----------

# 24. 공휴일 테이블 불러오기
df_holiday = spark.table("`1team-postgresql-connection_catalog`.silver.silver_holiday_list")

df_holiday.display()

# COMMAND ----------

# 25. 공휴일 테이블과 조인
df_final3 = df_final2.join(
    df_holiday.select("year", "month", "day").distinct().withColumn("date_kind", F.lit(1)),
    on=["year", "month", "day"],
    how="left"
).withColumn(
    "is_holiday",
    F.when(F.col("date_kind").isNotNull(), 1).otherwise(0)
).drop("date_kind")


df_final3.display()

# COMMAND ----------

df_final3.count()

# COMMAND ----------

# 26. 기상 테이블 불러오기
df_weather = spark.table("`1team-postgresql-connection_catalog`.silver.silver_temperature")

df_weather.display()

# COMMAND ----------

# 27. 필요한 컬럼 추출, month 컬럼 0 추가
df_weather2 = df_weather.select(
    "year", "month", "day", col("time").alias("scheduled_hour"),
    "wind_speed", "visibillity", "weather_phenomenon",
    "temperature", "dew_point_temp", "precipitation"
).distinct()

df_weather2 = df_weather2.withColumn(
    "month",
    lpad(col("month"), 2, "0")
)

df_weather2.display()

# COMMAND ----------

# 28. 메인 테이블과 조인
df_gold = df_final3.join(
    df_weather2,
    on=["year", "month", "day", "scheduled_hour"],
    how="left"
).orderBy(
    col("year").cast("int"),
    col("month").cast("int"),
    col("day").cast("int"),
    col("departure_hour").cast("int"),
    col("airline")
)

df_gold.display()

# COMMAND ----------

df_gold.count()

# COMMAND ----------

# 29. 기상 데이터 소수점 처리
df_gold =  df_gold.withColumn("temperature", format_number(col("temperature"), 2)) \
                            .withColumn("dew_point_temp", format_number(col("dew_point_temp"), 2))

df_gold.display()

# COMMAND ----------

df_gold2 =  df_gold.withColumn("final_est_passenger", format_number(col("final_est_passenger"), 2)) \
                            .withColumn("final_est_cargo", format_number(col("final_est_cargo"), 2))

df_gold2.display()

# COMMAND ----------

# 20.
# delayed_time 컬럼 정제
reg_df = df_gold2.withColumn(
    "delayed_time",
    when(col("delayed_time") < 0, 0)              # 조기출발(음수) → 0
    .when(col("delayed_time").isNull(), None)     # 취소 등 결측치는 그대로
    .otherwise(col("delayed_time"))               # 나머지는 그대로
)

reg_df.display()

# COMMAND ----------

# 21.
reg_df = reg_df.withColumn(
    "delay_category",
    when(col("delayed_time") < 25, "정상")
    .when(col("delayed_time") < 30, "경미한 지연")
    .when(col("delayed_time") < 40, "중간 지연")
    .otherwise("심각한 지연")
)

reg_df.display()

# COMMAND ----------

# 22.
reg_df.agg(
    _sum("final_est_passenger").alias("total_expected_passenger"),
    _sum("final_est_cargo").alias("total_expected_cargo")
).display()

# COMMAND ----------

# 26.
reg_df = (
    reg_df
    .withColumn("date", to_date(col("date")))  # 문자열 → 날짜(datetime)
    .withColumn("year", col("year").cast("int"))
    .withColumn("month", col("month").cast("int"))
    .withColumn("day", col("day").cast("int"))
    .withColumn("day_of_week", col("day_of_week").cast("int"))
    .withColumn("airline", col("airline").cast("string"))
    .withColumn("is_holiday", col("is_holiday").cast("int"))
    .withColumn("flight_number", col("flight_number").cast("string"))
    .withColumn("destination_city", col("destination_city").cast("string"))
    .withColumn("flight_type", col("flight_type").cast("string"))
    .withColumn("status", col("status").cast("string"))
    .withColumn("scheduled_time", col("scheduled_time").cast("string"))
    .withColumn("scheduled_hour", col("scheduled_hour").cast("int"))
    .withColumn("departure_time", col("departure_time").cast("string"))
    .withColumn("departure_hour", col("departure_hour").cast("int"))
    .withColumn("delayed_time", col("delayed_time").cast("int"))
    .withColumn("is_departed", col("is_departed").cast("int"))
    .withColumn("final_est_passenger", col("final_est_passenger").cast("float"))
    .withColumn("final_est_cargo", col("final_est_cargo").cast("float"))
    .withColumn("wind_speed", col("wind_speed").cast("int"))
    .withColumn("visibillity", col("visibillity").cast("int"))
    .withColumn("weather_phenomenon", col("weather_phenomenon").cast("int"))
    .withColumn("precipitation", col("precipitation").cast("int"))
)

reg_df.display()

# COMMAND ----------

# 23.
# 분위수 값 미리 계산
q1 = reg_df.approxQuantile("final_est_passenger", [0.2], 0.01)[0]
q2 = reg_df.approxQuantile("final_est_passenger", [0.7], 0.01)[0]

reg_df = reg_df.withColumn(
    "congestion_level",
    when(col("final_est_passenger") < q1, "여유")
    .when(col("final_est_passenger") < q2, "보통")
    .otherwise("혼잡")
)
reg_df.display()

# COMMAND ----------

reg_df.count()

# COMMAND ----------

# 24.
column_order = [
    # 날짜/시간
    "date", "year", "month", "day", "day_of_week", "is_holiday",
    "scheduled_time", "scheduled_hour", "departure_time", "departure_hour",

    # 항공편/운항 정보
    "airline", "flight_number","destination_city", "flight_type", 
    "final_est_passenger", "final_est_cargo","congestion_level",

    # 운항 상태/지연
    "status", "is_departed", "delayed_time", "delay_category", "delay_reason",

    # 기상/환경
    "wind_speed", "visibillity", "weather_phenomenon",
    "temperature", "dew_point_temp", "precipitation"
]
reg_df = reg_df.select(column_order)
reg_df.display()

# COMMAND ----------

# 27.
reg_df.agg(
    _sum("final_est_passenger").alias("total_expected_passenger"),
    _sum("final_est_cargo").alias("total_expected_cargo")
).show()

# COMMAND ----------

# 28.
# flight_type별 평균(expected_cargo) 구하기
reg_df.groupBy("flight_type").agg(
    F.avg("final_est_cargo").alias("avg_cargo"),
    F.sum("final_est_cargo").alias("sum_cargo"),
    F.count("*").alias("flight_count")
).orderBy("flight_type").display()

# COMMAND ----------

from functools import reduce
df_null = reg_df.filter(
    reduce(lambda x, y: x | y, (col(c).isNull() for c in reg_df.columns))
)
df_null.display()

# COMMAND ----------

reg_df = reg_df.dropna()

reg_df.count()

# COMMAND ----------

# 29. 
reg_df.orderBy(
    col("date"),
    col("year"),
    col("month"),
    col("day"),
    col("scheduled_time")
).write.mode("overwrite").saveAsTable("gold_test")

# COMMAND ----------

# 30.
host = "1dt-2nd-team1-postgres.postgres.database.azure.com"
port = "5432"
database = "postgres"
user = "azureuser"
password = "asdASD123!@#"
jdbc_url = f"jdbc:postgresql://{host}:{port}/{database}?sslmode=require"

reg_df.orderBy(
    col("date"),
    col("year"),
    col("month"),
    col("day"),
    col("scheduled_time")
).write.format("jdbc").option("url", jdbc_url).option("dbtable", "gold.gold_flight_info").option("user", user).option("password", password) \
    .option("driver", "org.postgresql.Driver") \
    .mode("append") \
    .save()

# COMMAND ----------

