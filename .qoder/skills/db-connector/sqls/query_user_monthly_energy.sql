-- 用户月度汇总实际用电量
SELECT
	b.company_name,
	sum(a.total_energy)/1000 '用户月度汇总实际用电量'
FROM `energy_vpp`.`user_energy` a join elec_company b
on a.orgcode = b.orgcode
WHERE 1=1
    AND a.`trade_center_id` = '27'
    AND a.`time` BETWEEN '20260401' AND '20260410'
    AND a.`vpp_id` = '1'
    AND a.`time_type` = '1'
    AND a.`company_id` IN (
        SELECT elec_company_id
        FROM user_contract_info
        WHERE trade_center_id = '27'
          AND vpp_id = '1'
          AND STATUS != 3
          AND contract_start_date <= '2026-04-30 00:00:00'
          AND contract_end_date >= '2026-04-01 00:00:00'
        --   AND elec_company_id IN ('3efe7a4a-6609-4c7d-bb9d-ca837daa7bb0', '5e6d26b2-c3e2-4092-b8ef-6fee67e9fa11')
    )
GROUP BY a.`company_id`;
