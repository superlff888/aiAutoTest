SELECT
	*
FROM
	`energy_vpp`.`vpp_energy`
WHERE
	`trade_center_id` = '{{trade_center_id}}'
	AND `time` >= REPLACE('{{start_date}}', '-', '')
	AND `time` <= REPLACE('{{end_date}}', '-', '')
	AND `vpp_id` = '{{vpp_id}}'
	AND `time_type` = '1'
GROUP BY time
ORDER BY time desc;