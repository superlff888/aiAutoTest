---
name: db-connector
description: 数据库连接器，支持 MySQL、PostgreSQL、SQLite 的连接管理和 SQL 执行。当用户提到"执行 SQL"、"连接数据库"、"查数据库"、"跑 SQL"时使用。
---

# DB Connector

数据库连接管理和 SQL 执行技能，支持 MySQL、PostgreSQL、SQLite。

## 脚本路径

`.claude/skills/db-connector/scripts/db_executor.py`

## 连接配置

test/prod 环境配置保存在 `.claude/.env` 文件中（已加入 `.gitignore`）：

```
TEST_MYSQL_HOST=...
TEST_MYSQL_PORT=3306
TEST_MYSQL_USER=...
TEST_MYSQL_PASSWORD=...
TEST_MYSQL_DATABASE=...

PROD_MYSQL_HOST=...
PROD_MYSQL_PORT=3306
PROD_MYSQL_USER=...
PROD_MYSQL_PASSWORD=...
PROD_MYSQL_DATABASE=...
```

## 命令

### 测试连接

```bash
python .claude/skills/db-connector/scripts/db_executor.py test test
python .claude/skills/db-connector/scripts/db_executor.py test prod
```

### 执行 SQL

```bash
python .claude/skills/db-connector/scripts/db_executor.py exec test --sql "SELECT ..."
python .claude/skills/db-connector/scripts/db_executor.py exec prod --sql "SELECT ..."
python .claude/skills/db-connector/scripts/db_executor.py exec test --file query.sql
```

### 内联连接（一次性使用，不依赖 .env）

```bash
python .claude/skills/db-connector/scripts/db_executor.py exec --inline \
  --host <主机> --port <端口> --user <用户名> --password <密码> --database <库名> \
  --sql "SELECT ..."
```

## 交互规则

- 用户使用已保存的连接名称（test/prod）时，直接用 `exec <名称>` 执行
- SQL 执行结果以表格格式输出，显示行数和列名
- 遇到 DDL/DROP/DELETE 等危险操作时，执行前必须向用户确认
- 查询超过 1000 行时提醒用户考虑加 LIMIT

## 安全注意事项

- 连接信息保存在 `.claude/.env` 中（已加入 `.gitignore`，不提交到仓库）
- 不记录 SQL 执行结果到日志文件
- 生产环境删除/修改操作必须二次确认
