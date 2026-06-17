SELECT 
	DAY,
	CAST(JSON_EXTRACT(prices, '$.price[0]') AS DECIMAL(15,8)) * 1000.0 AS '0',
	CAST(JSON_EXTRACT(prices, '$.price[1]') AS DECIMAL(15,5)) * 1000.0 AS '1',
	CAST(JSON_EXTRACT(prices, '$.price[2]') AS DECIMAL(15,5)) * 1000.0 AS '2',
	CAST(JSON_EXTRACT(prices, '$.price[3]') AS DECIMAL(15,5)) * 1000.0 AS '3',
	CAST(JSON_EXTRACT(prices, '$.price[4]') AS DECIMAL(15,5)) * 1000.0 AS '4',
	CAST(JSON_EXTRACT(prices, '$.price[5]') AS DECIMAL(15,5)) * 1000.0 AS '5',
	CAST(JSON_EXTRACT(prices, '$.price[6]') AS DECIMAL(15,5)) * 1000.0 AS '6',
	CAST(JSON_EXTRACT(prices, '$.price[7]') AS DECIMAL(15,5)) * 1000.0 AS '7',
	CAST(JSON_EXTRACT(prices, '$.price[8]') AS DECIMAL(15,5)) * 1000.0 AS '8',
	CAST(JSON_EXTRACT(prices, '$.price[9]') AS DECIMAL(15,5)) * 1000.0 AS '9',
	CAST(JSON_EXTRACT(prices, '$.price[10]') AS DECIMAL(15,5)) * 1000.0 AS '10',
	CAST(JSON_EXTRACT(prices, '$.price[11]') AS DECIMAL(15,5)) * 1000.0 AS '11',
	CAST(JSON_EXTRACT(prices, '$.price[12]') AS DECIMAL(15,5)) * 1000.0 AS '12',
	CAST(JSON_EXTRACT(prices, '$.price[13]') AS DECIMAL(15,5)) * 1000.0 AS '13',
	CAST(JSON_EXTRACT(prices, '$.price[14]') AS DECIMAL(15,5)) * 1000.0 AS '14',
	CAST(JSON_EXTRACT(prices, '$.price[15]') AS DECIMAL(15,5)) * 1000.0 AS '15',
	CAST(JSON_EXTRACT(prices, '$.price[16]') AS DECIMAL(15,5)) * 1000.0 AS '16',
	CAST(JSON_EXTRACT(prices, '$.price[17]') AS DECIMAL(15,5)) * 1000.0 AS '17',
	CAST(JSON_EXTRACT(prices, '$.price[18]') AS DECIMAL(15,5)) * 1000.0 AS '18',
	CAST(JSON_EXTRACT(prices, '$.price[19]') AS DECIMAL(15,5)) * 1000.0 AS '19',
	CAST(JSON_EXTRACT(prices, '$.price[20]') AS DECIMAL(15,5)) * 1000.0 AS '20',
	CAST(JSON_EXTRACT(prices, '$.price[21]') AS DECIMAL(15,5)) * 1000.0 AS '21',
	CAST(JSON_EXTRACT(prices, '$.price[22]') AS DECIMAL(15,5)) * 1000.0 AS '22',
	CAST(JSON_EXTRACT(prices, '$.price[23]') AS DECIMAL(15,5)) * 1000.0 AS '23'
FROM market_day_price 
WHERE 1=1
	AND trade_center_id = '30'  -- 5山东  28云南 -- 四川  30福建
	AND price_type IN ('31')  -- 21 日前  22 实时  31合同  32现货
	AND (DAY BETWEEN '2026-03-01' AND '2026-03-31')
	AND `deleted` = '0'   
ORDER BY DAY ASC, price_type ASC;