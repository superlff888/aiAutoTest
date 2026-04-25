---
name: bug-rate
description: 自动计算千行 Bug 率，支持分支名、GitLab URL、Git Diff 和静态扫描四种模式
---

# 千行 Bug 率计算

## 触发方式
当用户提到：
- "计算千行bug率" / "算一下千行bug率" / "千行bug率"
- "对比master和main的代码变更" / "统计代码变更量"
- 输入 GitLab Compare 链接
- 输入分支名（如 `feature-4.5.5`）

## 交互规则

**除非遇到无法计算的情况，否则不要问任何问题，直接执行脚本。**

- **Bug 数：必问**，文案"bug数是："，拿到后直接执行。
- **项目名：能推断直接用，无法判断时才问**"项目名："。
- GitLab URL / 项目名 + 分支名：直接执行，问一次 bug 数。

## 执行步骤

### 模式一：分支模式（最简洁，推荐）

用户输入分支名 + 项目路径，自动与 master 对比：

```
python .claude/skills/bug-rate/scripts/bug_rate_calculator.py \
  --branch feature-4.5.5 --project group/project --bugs 10 --detail
```

默认域名 `gitlab.starcharge.com`，可换 `--domain`。

### 模式二：GitLab URL 模式（无需 clone）

用户输入 GitLab Compare URL 时，直接调用 API：

```
python .claude/skills/bug-rate/scripts/bug_rate_calculator.py \
  --gitlab-url "https://gitlab.xxx/group/proj/-/compare/master...release-1.0" --bugs 10 --detail
```

Token 已内置，无需每次传参（如需换 token 用 `--token glpat-xxx` 覆盖）。

### 模式三：Git Diff 模式（本地仓库）

仓库已 clone 到本地时：

```
cd <项目目录>
python .claude/skills/bug-rate/scripts/bug_rate_calculator.py \
  --diff master main --bugs 10 --detail
```

### 模式四：静态扫描模式

```
python .claude/skills/bug-rate/scripts/bug_rate_calculator.py --dir <目录> --bugs 10
```

## 输出格式

用表格格式向用户展示：
- 变更文件数、新增行、更新行、删除行、变更总量、千行 Bug 率
- 按模块（一级子目录）分组汇总
- `--detail` 时显示文件级明细

## 脚本路径
`.claude/skills/bug-rate/scripts/bug_rate_calculator.py`

## 统计规则
- **新增行**：基准分支没有，目标分支有的行
- **更新行**：两个分支都有但内容被修改的行（= min(新增, 删除)）
- **删除行**：基准分支有，目标分支没有的行
- **变更总量** = 新增行 + 更新行 + 删除行
- **千行 Bug 率** = Bug 数 / 变更总量 × 1000

## Token 管理
- Token 已内置，默认使用
- 如需使用其他 token，通过 `--token glpat-xxx` 参数或 `GITLAB_TOKEN` 环境变量覆盖
- 脚本不保存 Token，仅用于当次 API 调用
- 需要 `read_api` 权限
- 目标分支必须未被合并到 master，否则 API 返回空
