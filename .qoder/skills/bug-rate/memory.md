---
name: bug-rate-skill
description: bug-rate 技能用于自动计算千行 Bug 率
type: project
---

bug-rate 技能用于自动计算千行 Bug 率，支持分支名、单/多 GitLab URL、Git Diff 和静态扫描五种模式。

## 输出风格

执行 bug-rate 技能后，**只展示结果表格**，不要追加"🛠 仍需换路"、"请选 A/B/C"等换路建议或额外提示文字。

- 脚本成功 → 只输出结果表格。
- 脚本失败 → 用**表格**列出每个 URL/分支的状态（一句话点明即可），不要画蛇添足列替代方案、不要输出"🛠 仍需换路"。失败时也走表格形式，不是一句话。

## 询问风格

模式确定后，**用 AskUserQuestion 弹选项**，不要用自然语言问。

- **GitLab URL 模式**：用 AskUserQuestion 弹 2 个选项：
  - `输入 GitLab Compare 链接`（description：贴单个或多个 URL）
  - `沿用历史使用过的链接`（description：复用上次用过的链接）
  - header = `链接来源`
  - 选"沿用"→ 直接拿上一次的 URL 列表（同一 session 内 Claude 上下文自带）执行；选"输入"→ 让用户贴。
