SELECT t.*, r."重要区域" FROM (
  SELECT
    "开始时间",
    "结束时间",
    '4G' AS "制式",
    "PLMN" || '-' || "eNodeB" || '-' || "CellID" AS "CGI",
    "小区名称",
    "最大用户数",
    "上行利用率",
    "下行利用率",
    CASE
      WHEN ("最大用户数" + 0 > 80) 
          AND (("上行利用率" + 0 > 0.7) OR ("下行利用率" + 0 > 0.7))
      THEN '是'
      ELSE '否'
    END AS "是否高负荷小区",
    CASE
      WHEN "PLMN" || '-' || "eNodeB" || '-' || "CellID" IN (SELECT "CGI" FROM "长期问题小区清单" WHERE "长期问题类型" = '高负荷')
      THEN '否'
      ELSE '是'
    END AS "是否突发高负荷"
  FROM "4G指标" 
  WHERE 
    "是否高负荷小区" = '是'
    AND "开始时间" >= '{{start_time}}'
    AND "结束时间" <= '{{end_time}}'
  UNION ALL
  SELECT
    "开始时间",
    "结束时间",
    '5G' AS "制式",
    "PLMN" || '-' || "gNBId" || '-' || "CellID" AS "CGI",
    "小区名称",
    "最大用户数",
    "上行利用率",
    "下行利用率",
    CASE
      WHEN ("最大用户数" + 0 > 100) 
          AND (("上行利用率" + 0 > 0.8) OR ("下行利用率" + 0 > 0.8))
      THEN '是'
      ELSE '否'
    END AS "是否高负荷小区",
    CASE
      WHEN "PLMN" || '-' || "gNBId" || '-' || "CellID" IN (SELECT "CGI" FROM "长期问题小区清单" WHERE "长期问题类型" = '高负荷')
      THEN '否'
      ELSE '是'
    END AS "是否突发高负荷"
  FROM "5G指标" 
  WHERE 
    "是否高负荷小区" = '是'
    AND "开始时间" >= '{{start_time}}'
    AND "结束时间" <= '{{end_time}}'
) t LEFT JOIN "重要监控区域清单" r ON t."CGI" = r."CGI"