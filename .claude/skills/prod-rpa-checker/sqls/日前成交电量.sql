SELECT
    *
FROM
	spot_energy
WHERE
	trade_center_id = '{{trade_center_id}}'
	AND vpp_id = '{{vpp_id}}'
	AND `transaction_cycle` = '21'
	AND `day` >= DATE_FORMAT(CURDATE(), '%Y%m01')
	AND `day` <= DATE_FORMAT(DATE_ADD(NOW(), INTERVAL -{{offset_days}} DAY), '%Y-%m-%d')
ORDER BY DAY desc;