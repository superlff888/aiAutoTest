---
name: bug-rate
description: 自动计算千行 Bug 率，对比 Git 分支变更行数
---

# 千行 Bug 率计算

## 触发方式
当用户提到：
- "计算千行bug率" / "算一下千行bug率"
- "对比master和main的代码变更"
- "统计代码变更量" / "看diff了多少行"
- "千行bug率"

## 执行步骤

1. 进入 `lee` 目录运行脚本：
   ```
   cd lee && python bug_rate_calculator.py --diff master main --bugs 10 --detail
   ```

2. 如果用户指定了其他分支、Bug 数或变更范围，替换参数：
   - `--diff <base> <target>` 指定对比分支
   - `--bugs <n>` 指定 Bug 总数
   - 加 `--detail` 显示文件级明细

3. 用表格格式向用户展示汇总结果：
   - 变更文件数、新增行、更新行、删除行、变更总量、千行 Bug 率
   - 文件级明细（状态、新增/更新/删除行数）

## 脚本路径
`lee/bug_rate_calculator.py`

## 统计规则
- **新增行**：master 没有，main 有的代码行
- **更新行**：两个分支都有但内容被修改的代码行
- **删除行**：master 有，main 没有的代码行
- **变更总量** = 新增行 + 更新行 + 删除行
- **千行 Bug 率** = Bug 数 / 变更总量 × 1000
