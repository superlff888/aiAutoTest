# 千行 Bug 率计算技能（bug-rate）

## 功能说明

自动计算千行 Bug 率，通过 GitLab API 或本地仓库对比两个分支之间的代码变更量，结合 Bug 数统计得出结果。

## 支持模式

| 模式 | 说明 | 适用场景 |
|------|------|---------|
| 分支模式 | 输入分支名，自动与 master 对比 | 本地已 clone 仓库 |
| GitLab URL 模式 | 输入 GitLab Compare 链接 | 远程对比，无需 clone |
| 多 URL 汇总模式 | 输入多个 Compare 链接 | 跨多个服务统一计算 |
| Git Diff 模式 | 本地仓库两个分支对比 | 本地仓库对比 |
| 静态扫描模式 | 扫描指定目录的变更量 | 静态分析 |

## 使用方式

```bash
# 分支模式（推荐）
python .claude/skills/bug-rate/scripts/bug_rate_calculator.py \
  --branch feature-4.5.5 --project group/project --bugs 10 --detail

# GitLab URL 模式
python .claude/skills/bug-rate/scripts/bug_rate_calculator.py \
  --gitlab-url "https://gitlab.starcharge.com/group/proj/-/compare/master...release-1.0" --bugs 10

# 多 URL 汇总
python .claude/skills/bug-rate/scripts/bug_rate_calculator.py \
  --gitlab-urls "url1" "url2" --bugs 10 --detail

# Git Diff 模式
cd <项目目录>
python .claude/skills/bug-rate/scripts/bug_rate_calculator.py \
  --diff master main --bugs 10

# 静态扫描模式
python .claude/skills/bug-rate/scripts/bug_rate_calculator.py --dir <目录> --bugs 10
```

## 统计规则

- **新增行**：基准分支没有，目标分支有的行
- **更新行**：两个分支都有但内容被修改的行（= min(新增, 删除)）
- **删除行**：基准分支有，目标分支没有的行
- **变更总量** = 新增行 + 更新行 + 删除行
- **千行 Bug 率** = Bug 数 / 变更总量 × 1000

## Token 管理

- Token 已内置，默认使用
- 可通过 `--token` 参数或 `GITLAB_TOKEN` 环境变量覆盖
- 脚本不保存 Token，仅用于当次 API 调用
- 需要 `read_api` 权限

## 文件结构

```
bug-rate/
├── SKILL.md                          # 技能定义和执行规则
├── memory.md                         # 业务上下文
├── README.md                         # 本文件
└── scripts/
    ├── bug_rate_calculator.py        # Python 计算脚本
    └── config.json                   # 配置文件
```
