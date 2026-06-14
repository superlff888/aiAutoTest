# P0-1 数据模型与 Pydantic 重构

> **状态**：✅ 已确定
> **优先级**：P0（必修）
> **影响文件**：`tools/data_model.py`、`workflow/case_generator.py`

---

## 1. 问题定位

| 文件 | 行号 | 当前内容 | 问题 |
|------|------|---------|------|
| `data_model.py` | 22 | `GenerateCase.except_result` | ❌ 拼写错误 |
| `case_generator.py` | 82 | `GenerateCase.except_result` | ❌ 拼写错误 |
| `generate_case_prompt.py` | 101 | 提示词要求 LLM 输出 `expected_result` | ✅ 正确 |
| `case_review_prompt.py` | 36 | 评审提到 `expected_result` | ✅ 正确 |

**后果**：LLM 输出 `expected_result`，落库时进 case.json 没问题，但任何基于 Pydantic 模型做后续处理（`with_structured_output`、序列化、API 返回）都会字段丢失。

---

## 2. 修复策略

1. **统一字段名** `except_result` → `expected_result`
2. **字段顺序对齐**到提示词要求
3. **新增 3 个 Pydantic 模型**供 `with_structured_output` 使用：
   - `CaseList`（用例列表）
   - `CoverageResult`（覆盖率结果）
   - `ReviewResult`（评审结果）

---

## 3. 代码改动

### 3.1 `tools/data_model.py`（全文替换）

```python
# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\05用例生成agent\03用例生成+数据存储集成Agent\rag_agent\tools\data_model.py
# @Author      : Lee大侠
# @Desc        : 测试用例 Pydantic 数据模型
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/06/14
# ========================================================


from typing import List, Optional
from pydantic import BaseModel, Field


class GenerateCase(BaseModel):
    """测试用例数据模型 - 与 generate_case_prompt.py 输出字段保持一致"""
    case_id: str = Field(..., description="用例编号，格式 TC-FUNC-001 依次递增")
    priority: str = Field(..., description="优先级，P0/P1/P2")
    case_name: str = Field(..., description="用例名称，简明描述验证目的")
    setup: List[str] = Field(default_factory=list, description="前置条件")
    test_data: dict = Field(default_factory=dict, description="测试数据")
    execute_step: List[str] = Field(..., description="操作步骤")
    expected_result: List[str] = Field(..., description="预期结果，关键断言")
    result: Optional[str] = Field(None, description="实际结果，初始为 null")
    # 用例管理的需求编号 - 由调用方注入，LLM 不需要生成
    requirement_id: Optional[str] = Field(None, description="需求编号，调用方注入")


class CaseList(BaseModel):
    """用例列表 - 用于 hybrid_structured_invoke 强校验"""
    cases: List[GenerateCase] = Field(..., description="用例列表")


class CoverageResult(BaseModel):
    """覆盖率检查结果 - 用于 hybrid_structured_invoke 强校验"""
    coverage_report: str = Field(..., description="覆盖率分析说明，150 字以内")
    coverage: str = Field(..., description='百分比格式，如 "100.0%"、"75.0%"，保留一位小数')
    recommend: List[str] = Field(default_factory=list, description="未完全覆盖的测试点清单")


class ReviewResult(BaseModel):
    """用例评审结果 - 用于 hybrid_structured_invoke 强校验"""
    review_result: str = Field(..., description='"通过" 或 "不通过"')
    review_desc: str = Field(..., description="评审结论说明，50 字以内")
    failed_dimensions: List[str] = Field(default_factory=list, description="不通过的维度名称")
```

### 3.2 `workflow/case_generator.py`（删除重复 Pydantic 定义，改 import）

```python
# 删除第 51 行附近的 GenerateCase 和 CaseList 类（共 18 行）
# 替换为：
from rag_agent.tools.data_model import GenerateCase, CaseList, CoverageResult, ReviewResult
```

### 3.3 全局搜索替换

```bash
# 在 03 目录下执行
grep -rn "except_result" lee/05用例生成agent/03用例生成\&数据存储集成Agent/ --include="*.py"
# 全部替换为 expected_result
```

---

## 4. 验证方法

```python
# quick_test_p0_1.py
from rag_agent.tools.data_model import GenerateCase, CaseList, CoverageResult, ReviewResult

# 1. 字段名正确性
c = GenerateCase(
    case_id="TC-FUNC-001",
    priority="P0",
    case_name="test",
    setup=[],
    test_data={},
    execute_step=["step1"],
    expected_result=["result1"],  # 不报错
)
print(c.expected_result)  # 输出 ['result1']

# 2. 三个新增模型可实例化
cl = CaseList(cases=[c])
cr = CoverageResult(coverage_report="测试", coverage="100.0%", recommend=[])
rr = ReviewResult(review_result="通过", review_desc="ok", failed_dimensions=[])
print("全部 OK")
```
