# 千行 Bug 率计算技能（bug-rate）

## 功能说明

自动计算千行 Bug 率，支持以下五种模式：

- **分支模式**：输入分支名，自动与 master 对比
- **GitLab URL 模式**：输入单个 GitLab Compare URL
- **多 GitLab URL 汇总模式**：输入多个 URL 汇总 diff
- **Git Diff 模式**：本地仓库 diff 对比
- **静态扫描模式**：扫描目录计算代码行数

## 使用方式

```bash
python .claude/skills/bug-rate/scripts/bug_rate_calculator.py \
  --branch feature-4.5.5 --project group/project --bugs 10 --detail
```

## 文件结构

```
bug-rate/
├── SKILL.md                           # 技能定义
└── scripts/
    ├── bug_rate_calculator.py         # Python 计算脚本
    └── config.json                    # 配置文件
```
