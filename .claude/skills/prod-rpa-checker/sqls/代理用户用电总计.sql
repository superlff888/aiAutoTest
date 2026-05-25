SELECT
	*
FROM
	`energy_vpp`.`vpp_energy`
WHERE
	`trade_center_id` = '{{trade_center_id}}'
	AND `time` >= DATE_FORMAT(CURDATE(), '%Y%m01')
	AND `time` <= DATE_FORMAT(DATE_ADD(NOW(), INTERVAL -{{offset_days}} DAY), '%Y%m%d')
	AND `vpp_id` = '{{vpp_id}}'
	AND `time_type` = '1'
GROUP BY time
ORDER BY time desc;