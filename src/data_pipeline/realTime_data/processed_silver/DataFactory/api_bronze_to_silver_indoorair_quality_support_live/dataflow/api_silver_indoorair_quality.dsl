source(output(
		timestamp as string,
		terminalid as string,
		rtime as string,
		co2 as double,
		pm10 as double,
		pm2_5 as double,
		co as double,
		no2 as double
	),
	allowSchemaDrift: true,
	validateSchema: false,
	isolationLevel: 'READ_UNCOMMITTED',
	format: 'table') ~> source1
source1 derive(year = substring(rtime, 0, 4),
		month = substring(rtime, 5, 2),
		day = substring(rtime, 7, 2),
		hour_of_day = substring(rtime, 9, 2),
		co2_label = case(
  co2 <= 450, '좋음',
  co2 <= 699, '보통',
  co2 <= 1000, '나쁨',
  '매우 나쁨'
),
		pm10_label = case(
  pm10 <= 30, '좋음',
  pm10 <= 80, '보통',
  pm10 <= 150, '나쁨',
  '매우 나쁨'
),
		pm2_5_label = case(
  pm2_5 <= 15, '좋음',
  pm2_5 <= 35, '보통',
  pm2_5 <= 75, '나쁨',
  '매우 나쁨'
),
		co_label = case(
  co <= 9, '좋음',
  co <=15, '보통',
  co <= 25, '나쁨',
  '매우 나쁨'
),
		no2_label = case(
  no2 <= 0.03, '좋음',
  no2 <= 0.06, '보통',
  no2 <= 0.10, '나쁨',
  '매우 나쁨'
),
		total_indoorair_quality_label = case(
  greatest(
    case(co2 <= 450, 1, co2 <= 699, 2, co2 <= 1000, 3, 4),
    case(pm10 <= 30, 1, pm10 <= 80, 2, pm10 <= 150, 3, 4),
    case(pm2_5 <= 15, 1, pm2_5 <= 35, 2, pm2_5 <= 75, 3, 4),
    case(co <= 9, 1, co <= 25, 3, 4),
    case(no2 <= 0.03, 1, no2 <= 0.06, 2, no2 <= 0.10, 3, 4)
  ) 
  == 1, '좋음',
  greatest(
    case(co2 <= 450, 1, co2 <= 699, 2, co2 <= 1000, 3, 4),
    case(pm10 <= 30, 1, pm10 <= 80, 2, pm10 <= 150, 3, 4),
    case(pm2_5 <= 15, 1, pm2_5 <= 35, 2, pm2_5 <= 75, 3, 4),
    case(co <= 9, 1, co <= 25, 3, 4),
    case(no2 <= 0.03, 1, no2 <= 0.06, 2, no2 <= 0.10, 3, 4)
  ) 
  == 2, '보통',
  greatest(
    case(co2 <= 450, 1, co2 <= 699, 2, co2 <= 1000, 3, 4),
    case(pm10 <= 30, 1, pm10 <= 80, 2, pm10 <= 150, 3, 4),
    case(pm2_5 <= 15, 1, pm2_5 <= 35, 2, pm2_5 <= 75, 3, 4),
    case(co <= 9, 1, co <= 25, 3, 4),
    case(no2 <= 0.03, 1, no2 <= 0.06, 2, no2 <= 0.10, 3, 4)
  ) 
  == 3, '나쁨',
  '매우 나쁨'
)) ~> derivedColumn1
select1 sort(asc(timestamp, true),
	asc(rtime, true)) ~> sort1
derivedColumn1 select(mapColumn(
		timestamp,
		rtime,
		year,
		month,
		day,
		hour_of_day,
		terminalid,
		co2,
		pm10,
		pm2_5,
		co,
		no2,
		co2_label,
		pm10_label,
		pm2_5_label,
		co_label,
		no2_label,
		total_indoorair_quality_label
	),
	skipDuplicateMapInputs: true,
	skipDuplicateMapOutputs: true) ~> select1
sort1 sink(allowSchemaDrift: true,
	validateSchema: false,
	input(
		timestamp as string,
		rtime as string,
		year as string,
		month as string,
		day as string,
		hour_of_day as string,
		terminalid as string,
		co2 as string,
		pm10 as string,
		pm2_5 as string,
		co as string,
		no2 as string,
		co2_label as string,
		pm10_label as string,
		pm2_5_label as string,
		co_label as string,
		no2_label as string,
		total_indoorair_quality_label as string
	),
	deletable:false,
	insertable:true,
	updateable:false,
	upsertable:false,
	format: 'table',
	skipDuplicateMapInputs: true,
	skipDuplicateMapOutputs: true) ~> sink1