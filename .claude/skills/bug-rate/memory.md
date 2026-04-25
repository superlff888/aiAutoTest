---
name: bug-rate-workflow
description: 千行 Bug 率计算的交互规则：bug数必问，项目名能不问就不问
type: feedback
---

## 千行 Bug 率计算的交互规则

**Bug 数：每次都问，文案"bug数是："。这是计算千行 Bug 率的必要参数。**

**项目名：用户提供时直接用，不提供时才问"项目名："。**

**其他信息：一概不问。**

**已知项目：** vpp-web、vpp-operation、vpp-operation-bff、vpp-market-info-service

**How to apply：** 触发 bug-rate 时，项目名在已知列表中就直接执行（用 --bugs 10），不在列表中才问"项目名："；bug 数每次都问；拿到两个参数后直接执行脚本，不做额外确认。
