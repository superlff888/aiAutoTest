SELECT
	*
FROM
	`energy_vpp`.`market_day_price`
WHERE
	`trade_center_id` = '{{trade_center_id}}'
	AND `deleted` = '0'
	AND `day` >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
	AND `day` <= DATE_FORMAT(DATE_ADD(NOW(), INTERVAL -{{offset_days}} DAY), '%Y-%m-%d')
	AND `price_type` in ( '22' )
ORDER BY
	`day` desc
;