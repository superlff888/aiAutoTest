SELECT
	*
FROM
	`energy_vpp`.`market_day_price`
WHERE
	`trade_center_id` = '{{trade_center_id}}'
	AND `deleted` = '0'
	AND `day` >= '{{start_date}}'
	AND `day` <= '{{end_date}}'
	AND `price_type` in ( '11' )
ORDER BY
	`day` desc
;