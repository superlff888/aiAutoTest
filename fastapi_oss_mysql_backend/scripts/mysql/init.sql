-- MySQL 初始化脚本（容器首次启动时自动执行）
-- 用于 docker-compose 启动时创建数据库

CREATE DATABASE IF NOT EXISTS `fastapi_demo`
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

-- 创建只读用户（可选）
-- CREATE USER 'fastapi_readonly'@'%' IDENTIFIED BY 'readonly123';
-- GRANT SELECT ON fastapi_demo.* TO 'fastapi_readonly'@'%';
-- FLUSH PRIVILEGES;

SELECT '✅ 数据库 fastapi_demo 初始化完成' AS message;
