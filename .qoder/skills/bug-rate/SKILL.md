---
name: bug-rate
description: 自动计算千行 Bug 率，支持分支名、单/多 GitLab URL、Git Diff 和静态扫描五种模式，按 hunk 分组精确计算
---

# 千行 Bug 率计算

## 触发方式

当用户提到：

- "计算千行bug率" / "算一下千行bug率" / "千行bug率"
- "对比master和main的代码变更" / "统计代码变更量"
- 输入单个或多个 GitLab Compare 链接
- 输入分支名（如 `feature-4.5.5`）

## 交互规则（每次必问）

**每次触发 bug-rate 技能，第一步必须先用 `AskUserQuestion` 工具同时弹出两个核心问题，拿到答案后再走后续流程。不要替用户做主、不要凭默认值绕过。**

### 必问的两个问题

**问题 1：采用哪种计算模式？**（单选，header=`计算模式`）

| option | label | description |
|--------|-------|-------------|
| 1 | 分支模式 | 提供 GitLab 项目名 + 分支名，自动与 master 对比（推荐） |
| 2 | GitLab URL | 提供 GitLab Compare 链接（单个或多个），无需 clone |
| 3 | 本地 Git Diff | 在本地仓库中执行 git diff 两个分支/tag |
| 4 | 静态扫描 | 扫描指定目录的所有 .py/.java/.js 等代码文件 |

**问题 2：本次发现的 Bug 数是多少？**（单选，header=`Bug 数`）

| option | label | description |
|--------|-------|-------------|
| 1 | 0 | 本次未发现 Bug |
| 2 | 1 | 发现 1 个 Bug |
| 3 | 5 | 发现 5 个 Bug |
| 4 | 10 | 发现 10 个 Bug |

### 拿到两个答案后的处理

- **Bug 数**：使用用户选中的值传给脚本的 `--bugs` 参数。若用户选了"Other"并填了自定义数字，直接用该数字。
- **计算模式**：决定后续要再追问什么参数，以及最终用哪条执行命令。
  - **分支模式**：再追问 `项目名`（如 `group/project`）和 `分支名`（如 `feature-4.5.5`），再执行。
  - **GitLab URL**：用 `AskUserQuestion` 弹 2 个选项（header=`链接来源`）：
    - `输入 GitLab Compare 链接`（description：贴单个或多个 URL）
    - `沿用历史使用过的链接`（description：复用上次用过的链接）
    - 选"输入"→ 让用户贴；选"沿用"→ 直接拿上一次的 URL 列表执行。
  - **本地 Git Diff**：再追问 `本地仓库路径` 和两个 `ref`（分支/tag/SHA），再执行。
  - **静态扫描**：再追问 `目录路径`，再执行。
- **项目名/路径等次要参数**：仅在执行模式需要时再追问；不要在第一轮问，避免一次性问太多。

### 唯一例外

如果用户**主动**在第一轮就把"模式 + 所需参数 + bug 数"一次性给齐了（例如直接说"用静态扫描扫 lee 目录，bug 数 5"），可以跳过 AskUserQuestion，直接执行。否则一律先问。

## 执行步骤

### 模式一：分支模式（最简洁，推荐）

用户输入分支名 + 项目路径，自动与 master 对比：

```bash
python .claude/skills/bug-rate/scripts/bug_rate_calculator.py \
  --branch feature-4.5.5 --project group/project --bugs 10 --detail
```

默认域名 `gitlab.starcharge.com`，可换 `--domain`。

### 模式二：GitLab URL 模式（无需 clone）

用户输入 GitLab Compare URL 时，直接调用 API：

```bash
python .claude/skills/bug-rate/scripts/bug_rate_calculator.py \
  --gitlab-url "https://gitlab.xxx/group/proj/-/compare/master...release-1.0" --bugs 10 --detail
```

**支持的 URL 格式：**

- 标准：`https://gitlab.xxx/group/proj/-/compare/master...release-1.0`
- 带 query：`...release-1.0?from_project_id=123`
- 带锚点：`...release-1.0#L10`（GitLab 页面跳转到第 10 行时的链接）
- 三者混合：脚本自动剥离 `?xxx` 和 `#xxx`，干净取分支名

Token 已内置，无需每次传参（如需换 token 用 `--token glpat-xxx` 覆盖）。

### 模式三：多 GitLab URL 汇总模式

用户输入多个 GitLab Compare URL（跨多个服务）时，汇总所有 diff 后统一计算：

```bash
python .claude/skills/bug-rate/scripts/bug_rate_calculator.py \
  --gitlab-urls "url1" "url2" "url3" --bugs 10 --detail
```

- 逐个解析每个 URL 的 diff，汇总新增/更新/删除行
- 文件路径标记 `[项目名]/实际路径`（项目名已 URL 反编码，可读性更好）
- 最终用**总变更量**和**总 Bug 数**计算一个统一的千行 Bug 率
- 按实际一级子目录分组（自动剥离 `[项目名]` 前缀）
- **部分失败容忍**：某个 URL 拿不到 diff 不影响其他 URL

### 模式四：Git Diff 模式（本地仓库）

仓库已 clone 到本地时：

```bash
cd <项目目录>
python .claude/skills/bug-rate/scripts/bug_rate_calculator.py \
  --diff master main --bugs 10 --detail
```

### 模式五：静态扫描模式

```bash
python .claude/skills/bug-rate/scripts/bug_rate_calculator.py --dir <目录> --bugs 10
```

## 输出格式

用表格格式向用户展示：

- 变更文件数、新增行、更新行、删除行、变更总量、千行 Bug 率
- 按模块（一级子目录）分组汇总
- `--detail` 时显示文件级明细

## 统计规则（按 hunk 精确计算）

```
新增行   = 基准分支没有，目标分支有的行
更新行   = 同一 hunk 内成对出现的增删（min(added, deleted)）
删除行   = 基准分支有，目标分支没有的行
变更总量 = 新增行 + 更新行 + 删除行
千行 Bug 率 = Bug 数 / 变更总量 × 1000
```

### 为什么"精确"？

核心算法采用**按 hunk 分组计算**，而非全文件混算：

```
git diff --unified=0 --diff-algorithm=patience
   ↓
按 @@ hunk 头切分（每个 hunk 是一次连续变更块）
   ↓
每个 hunk 独立套 min(added, deleted) 还原"修改"行
   ↓
汇总所有 hunk 的结果
```

**关键技术配合：**

| 手段 | 作用 |
|------|------|
| `--unified=0` | 不带上下文行，hunk 切得最碎 |
| `--diff-algorithm=patience` | 行配对符合语义 |
| 按 `@@` 切块 | 隔离无关变更，避免跨块错位配对 |
| 块内 `min()` | 还原"修改"语义 |

**对比示例**（同一文件：4 行修改 + 4 行删除 + 4 行新增分散在 2 个 hunk）：

| 方案 | updated | new_only | del_only | 偏差 |
|------|---------|----------|----------|------|
| 旧（全文件混算） | 5 | 0 | 3 | ❌ 偏 1 行 |
| 新（按 hunk） | 4 | 1 | 4 | ✅ 精确 |

## 特殊情况处理

| 场景 | 脚本行为 |
|------|---------|
| 分支已合并到 master | 输出 `⚠ 分支已合并到 master，变更已被吸收` |
| 分支不存在 / 404 | 输出 `项目或分支不存在` + GitLab 错误信息 |
| 多个 URL 中部分失败 | 失败的 URL 给出诊断，其他 URL 继续执行 |
| URL 带 `?from_project_id=xxx` 或 `#L10` | 自动剥离，干净取分支名 |
| Token 缺失 | 提示 `--token` 参数或 `GITLAB_TOKEN` 环境变量 |
| Windows GBK 终端乱码 | 脚本内强制 UTF-8 输出 |

## 脚本路径

`.claude/skills/bug-rate/scripts/bug_rate_calculator.py`

## Token 管理

- Token 已内置在 `scripts/config.json`，默认使用
- 优先级：命令行 `--token` > 环境变量 `GITLAB_TOKEN` > 配置文件
- 脚本不保存 Token，仅用于当次 API 调用
- 需要 `read_api` 权限
- 目标分支必须未被合并到 master，否则 API 返回空

## 更新记录

- **v2.0（本次升级）**
  - 核心算法升级：全文件混算 → 按 hunk 分组精确计算
  - 本地 Git 模式加 `--unified=0 --diff-algorithm=patience`
  - URL 正则防御性排除 `? # \s`
  - 多 URL 模式下项目名 URL 反编码优化
- **v1.0（初版）**
  - 五种模式（分支/单 URL/多 URL/本地 diff/静态扫描）
  - 基础千行 Bug 率计算
