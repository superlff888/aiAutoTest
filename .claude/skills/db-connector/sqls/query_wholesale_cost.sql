-- 月度批发市场度电成本、批发侧成本
SELECT
	CAST( JSON_EXTRACT ( bill_detail_after_adjust, '$.belongCompanyPowerCost' ) AS DECIMAL ( 15, 8 ) )*1000 AS '月度批发市场度电成本',
	CAST( JSON_EXTRACT ( bill_detail_after_adjust, '$.wholesaleCost' ) AS DECIMAL ( 15, 5 ) ) AS '批发侧成本'
from bill_info
WHERE
	trade_center_id = '27'
	AND MONTH IN ( '2026-04' )
	AND bill_type = 2;


-- 只需要通过修改belongCompanyPowerCost为4月前10天的度电成本
-- 只需要通过修改wholesaleCost为4月前10天的批发侧成本