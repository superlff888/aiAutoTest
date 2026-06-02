SELECT
    *
FROM
	spot_energy
WHERE
	trade_center_id = '{{trade_center_id}}'
	AND vpp_id = '{{vpp_id}}'
	AND `transaction_cycle` = '21'
	AND `day` >= '{{start_date}}'
	AND `day` <= '{{end_date}}'
ORDER BY DAY desc;