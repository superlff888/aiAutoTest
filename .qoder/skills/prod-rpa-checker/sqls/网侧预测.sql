SELECT
	*
FROM
	grid_data
WHERE
	trade_center_id = '{{trade_center_id}}'
	AND data_type = 2
	AND date >= '{{start_date}}'
	AND date <= '{{end_date}}'
ORDER BY
	date desc
;