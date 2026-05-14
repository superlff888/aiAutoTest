SELECT
    u.time,
    u.user_total_energy,
    v.vpp_total_energy,
    (u.user_total_energy - IFNULL(v.vpp_total_energy, 0)) AS diff_energy
FROM (
    SELECT
        time,
        SUM(total_energy) AS user_total_energy
    FROM user_energy
    WHERE trade_center_id = '{{trade_center_id}}'
      AND time BETWEEN DATE_FORMAT(CURDATE(), '%Y%m01') AND LAST_DAY(CURDATE())
    GROUP BY time
) u
LEFT JOIN (
    SELECT
        time,
        SUM(total_energy) AS vpp_total_energy
    FROM vpp_energy
    WHERE trade_center_id = '{{trade_center_id}}'
      AND time BETWEEN DATE_FORMAT(CURDATE(), '%Y%m01') AND LAST_DAY(CURDATE())
    GROUP BY time
) v
ON u.time = v.time
ORDER BY u.time;