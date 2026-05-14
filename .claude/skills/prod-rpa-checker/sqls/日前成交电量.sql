SELECT
    *
FROM
	spot_energy
WHERE
	trade_center_id = '{{trade_center_id}}'
	AND vpp_id = '8f3af8ed-b12b-451e-929c-88c46e9b892a'
	AND `transaction_cycle` = '21'
	AND `day` >= DATE_FORMAT(CURDATE(), '%Y%m01')
	AND `day` <= DATE_FORMAT(DATE_ADD(NOW(), INTERVAL -{{offset_days}} DAY), '%Y-%m-%d')
ORDER BY DAY desc;