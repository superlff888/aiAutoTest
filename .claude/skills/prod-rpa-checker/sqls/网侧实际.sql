SELECT
	*
FROM
	grid_data
WHERE
	trade_center_id = '{{trade_center_id}}'
	AND data_type = 2
	AND date >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
	AND date <= DATE_FORMAT(DATE_ADD(NOW(), INTERVAL -{{offset_days}} DAY), '%Y-%m-%d')
ORDER BY
	date desc
;