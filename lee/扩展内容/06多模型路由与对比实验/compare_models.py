# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee/06多模型路由与对比实验/compare_models.py
# @Author      : Lee大侠
# @Desc        : DeepSeek vs MiniMax-M3 用例生成对比评测脚本
# @CreateTime  : 2026/06/07
# @UpdateTime  : 2026/06/07
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


"""
DeepSeek-V4-Pro vs MiniMax-M3 用例生成能力对比
================================================

# 评测维度
    1. **质量**
        - 生成用例数
        - 字段完整率（case_id/case_name/setup/test_data/execute_step/expected_result/priority 都有）
        - 优先级分布合理度（P0:P1:P2 比例）
        - 评审通过率（自身评审节点的通过率）
    2. **性能**
        - 总耗时（生成 + 评审）
        - token 用量（input + output）
        - 估算成本
    3. **稳定性**
        - 异常次数
        - 字段缺失数

# 用法
    python compare_models.py                                 # 跑默认 3 份需求
    python compare_models.py --dataset my_cases.json        # 自定义需求集
    python compare_models.py --rounds 5 --models deepseek-v4-pro MiniMax-M3
    python compare_models.py --report md                    # 额外生成 Markdown 报告

# 输入格式（eval_dataset/requirements_samples.json）
    [
        {"id": "req_001", "name": "用户注册", "text": "..."},
        {"id": "req_002", "name": "用户登录", "text": "..."}
    ]
"""

from __future__ import annotations

import os
import sys
import json
import time
import argparse
import traceback
from copy import deepcopy
from typing import List, Dict, Any, Optional
from statistics import mean, pstdev

# 路径准备
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# 复用 model_router + 原项目 prompt
from model_router import (
    get_llm_for_task,
    reset_routing,
    set_routing,
    list_routing,
    get_usage_summary,
    USAGE_HISTORY,
    export_usage_history,
    TaskType,
)
from langchain.messages import SystemMessage, HumanMessage

# ============================默认评测集==========================
DEFAULT_DATASET_PATH = os.path.join(SCRIPT_DIR, "eval_dataset", "requirements_samples.json")

# 3 份差异化的需求（覆盖：单功能/含异常/含状态规则）
DEFAULT_REQUIREMENTS = [
    {
        "id": "req_001",
        "name": "用户注册（简单）",
        "text": """
F1.1 用户注册
新用户通过注册方式创建账户，支持邮箱/用户名+密码的注册方式。
🚶 主流程
1. 用户打开注册页，填写注册信息
2. 系统校验格式与唯一性（用户名、邮箱）
3. 提交注册，后台创建账户，初始状态为"正常"
4. 注册成功后自动登录并跳转首页
⚠️ 异常流程
● 邮箱/用户名已被注册：提示"已存在"
● 两次密码不一致：提示用户重新输入
📌 业务规则
● 用户名唯一，支持 4~20 位字母数字组合
● 密码长度不少于 6 位
● 邮箱必须符合格式 xxx@xxx.xx
""",
    },
    {
        "id": "req_002",
        "name": "商品加入购物车（中等）",
        "text": """
F2.3 商品加入购物车
🧩 功能背景
用户在浏览商品详情页时，可将商品加入购物车；同一个商品多次加入需按规则合并。
🚶 主流程
1. 用户点击"加入购物车"按钮
2. 前端校验登录态，未登录跳转登录页
3. 后端查询 SKU 库存
4. 库存充足则写入购物车，返回成功；库存不足返回错误码
5. 前端弹出"加入成功"Toast
📌 业务规则
● 同一 SKU 多次加入，购物车数量累加，不新增条目
● 单 SKU 数量上限 99
● 单购物车 SKU 种类上限 50
● 库存为 0 时按钮置灰不可点击
⚠️ 异常流程
● 库存不足：Toast 提示"库存仅剩 X 件"
● 用户未登录：跳转登录并保留来源页
● 限领/限购活动：按活动规则校验
""",
    },
    {
        "id": "req_003",
        "name": "订单取消（含状态流转）",
        "text": """
F3.7 订单取消
🧩 功能背景
用户在下单后、发货前可以取消订单；不同订单状态取消规则不同。
🚶 主流程
1. 用户进入"我的订单"，选择待支付/待发货订单
2. 点击"取消订单"，弹出原因选择
3. 提交后系统校验状态合法性
4. 校验通过：状态置为"已取消"，触发退款流程（如已支付）
5. 前端提示"取消成功"
📌 状态规则
● 待支付：可直接取消
● 待发货：可取消，已支付进入退款
● 已发货：不允许取消，引导"申请售后"
● 已完成/已取消：禁止重复操作
⚠️ 异常流程
● 状态已变更：提示"订单状态已更新，请刷新"
● 退款失败：重试 3 次，仍失败转人工
📌 业务规则
● 取消原因必填，限 200 字
● 同一订单 24 小时内最多取消 5 次（防误操作）
""",
    },
]

# ============================通用 prompt 模板（评测专用）==========================
# 为了公平对比，用一个"最小依赖"的 prompt：脱离原项目的复杂 prompt，
# 让对比更纯粹——只看模型本身的能力。
MINIMAL_CASE_PROMPT = """你是一位资深测试工程师。请根据用户提供的功能需求生成测试用例。
要求：
1. 覆盖正向主流程、边界值、异常分支
2. 不得推测需求中未提及的业务规则
3. 每条用例的优先级 P0=核心主流程，P1=边界/重要异常，P2=边缘异常/容错
4. 输出必须是**严格合法的 JSON 数组**，不要包含任何 Markdown 标记或解释性文字
5. 每条用例必须包含以下字段：case_id, priority, case_name, setup, test_data, execute_step, expected_result, result
6. case_id 格式 "TP-FUNC-001" 依次递增
"""


def _build_case_prompt(req_text: str):
    return [
        SystemMessage(content=MINIMAL_CASE_PROMPT),
        HumanMessage(content=f"请为以下需求生成测试用例：\n{req_text}"),
    ]


# ============================评测指标计算==========================
REQUIRED_FIELDS = ["case_id", "priority", "case_name", "setup",
                   "test_data", "execute_step", "expected_result"]


def _safe_loads(content: str) -> Any:
    """尽量把模型输出解析成 list[dict]；失败返回 []。"""
    if not isinstance(content, str):
        return content if isinstance(content, list) else []
    s = content
    if "<think>" in s:
        s = s.split("</think>")[-1]
    s = s.replace("```json", "").replace("```", "").strip()
    try:
        data = json.loads(s)
    except Exception:
        return []
    return data if isinstance(data, list) else data.get("cases", [])


def _calc_field_completeness(cases: List[dict]) -> float:
    """字段完整率：所有用例中"必备字段都不缺"的比例。"""
    if not cases:
        return 0.0
    ok = 0
    for c in cases:
        if all(c.get(f) not in (None, "", [], {}) for f in REQUIRED_FIELDS):
            ok += 1
    return round(ok / len(cases), 4)


def _calc_priority_dist(cases: List[dict]) -> Dict[str, int]:
    """P0/P1/P2 数量分布。"""
    dist = {"P0": 0, "P1": 0, "P2": 0, "other": 0}
    for c in cases:
        p = str(c.get("priority", "")).strip().upper()
        dist[p if p in dist else "other"] += 1
    return dist


def _self_review(llm, req_text: str, case: dict) -> str:
    """让同一模型评审自己生成的某条用例，返回 "通过"/"不通过"。"""
    prompt = [
        SystemMessage(content="你是测试评审专家。仅输出严格 JSON：{\"verdict\":\"通过\"或\"不通过\",\"reason\":\"<20字内理由\"}"),
        HumanMessage(content=f"需求：\n{req_text}\n\n用例：\n{json.dumps(case, ensure_ascii=False)}"),
    ]
    try:
        resp = llm.invoke(prompt)
        data = _safe_loads(resp.content)
        if isinstance(data, list) and data:
            data = data[0]
        return data.get("verdict", "未通过") if isinstance(data, dict) else "未通过"
    except Exception:
        return "异常"


# ============================单模型跑一份需求==========================
def run_one(llm, req: Dict[str, Any]) -> Dict[str, Any]:
    """
    用指定 llm 跑一份需求：生成 + 自评 + 简单覆盖检测。
    返回该份需求的指标 dict。
    """
    req_id = req["id"]
    req_name = req["name"]
    req_text = req["text"]
    print(f"\n>>> [{llm.model_name}] 跑需求 {req_id} - {req_name}")

    t0 = time.time()
    cases: List[dict] = []
    error: Optional[str] = None
    try:
        # 1) 生成
        resp = llm.invoke(_build_case_prompt(req_text))
        cases = _safe_loads(resp.content)
        if not isinstance(cases, list):
            cases = []
        print(f"    生成用例数：{len(cases)}")
    except Exception as e:
        error = f"生成异常：{e}"
        print(f"    {error}")

    # 2) 自评（采样前 5 条，节省时间）
    review_passed = 0
    review_total = 0
    sample = cases[:5]
    for c in sample:
        v = _self_review(llm, req_text, c)
        review_total += 1
        if v == "通过":
            review_passed += 1
    review_rate = round(review_passed / review_total, 4) if review_total else 0.0

    # 3) 覆盖检测（粗略：让模型回答"覆盖率"）
    coverage_pct = 0
    try:
        cov_prompt = [
            SystemMessage(content="你是测试覆盖率分析专家。阅读需求与用例，给出整体覆盖率（0~100 的整数），仅输出 JSON：{\"coverage\": 80}"),
            HumanMessage(content=f"需求：\n{req_text}\n\n用例：\n{json.dumps(cases, ensure_ascii=False)}"),
        ]
        cov_resp = llm.invoke(cov_prompt)
        cov_data = _safe_loads(cov_resp.content)
        if isinstance(cov_data, list) and cov_data:
            cov_data = cov_data[0]
        coverage_pct = int(cov_data.get("coverage", 0)) if isinstance(cov_data, dict) else 0
    except Exception as e:
        print(f"    覆盖检测异常：{e}")

    elapsed = round(time.time() - t0, 2)

    return {
        "req_id": req_id,
        "req_name": req_name,
        "model": llm.model_name,
        "case_count": len(cases),
        "field_completeness": _calc_field_completeness(cases),
        "priority_dist": _calc_priority_dist(cases),
        "self_review_passed": review_passed,
        "self_review_total": review_total,
        "self_review_rate": review_rate,
        "coverage_pct": coverage_pct,
        "elapsed_sec": elapsed,
        "error": error,
        "cases_sample": cases[:3],   # 存前 3 条作为样本，便于人工比对
    }


# ============================汇总对比==========================
def aggregate(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """按模型聚合：求均值/总数。"""
    by_model: Dict[str, List[Dict[str, Any]]] = {}
    for r in records:
        by_model.setdefault(r["model"], []).append(r)

    summary = {}
    for model, rs in by_model.items():
        n = len(rs)
        summary[model] = {
            "样本数": n,
            "平均生成用例数": round(mean([r["case_count"] for r in rs]), 2),
            "平均字段完整率": round(mean([r["field_completeness"] for r in rs]), 4),
            "平均自评通过率": round(mean([r["self_review_rate"] for r in rs]), 4),
            "平均覆盖率(自检)": round(mean([r["coverage_pct"] for r in rs]), 2),
            "平均耗时(秒)": round(mean([r["elapsed_sec"] for r in rs]), 2),
            "异常次数": sum(1 for r in rs if r["error"]),
        }
    return summary


# ============================Markdown 报告==========================
def to_markdown(records: List[Dict[str, Any]], summary: Dict[str, Any],
                usage: Dict[str, Any]) -> str:
    lines = ["# DeepSeek-V4-Pro vs MiniMax-M3 用例生成对比报告\n"]
    lines.append(f"生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    lines.append(f"评测样本数：{len({r['req_id'] for r in records})} 份需求\n")
    lines.append("\n## 一、汇总对比\n")
    lines.append("| 模型 | 样本数 | 平均生成用例数 | 字段完整率 | 自评通过率 | 自检覆盖率 | 平均耗时(s) | 异常次数 |")
    lines.append("|------|--------|----------------|------------|------------|------------|-------------|----------|")
    for model, s in summary.items():
        lines.append(f"| {model} | {s['样本数']} | {s['平均生成用例数']} | "
                     f"{s['平均字段完整率']:.2%} | {s['平均自评通过率']:.2%} | "
                     f"{s['平均覆盖率(自检)']}% | {s['平均耗时(秒)']} | {s['异常次数']} |")

    lines.append("\n## 二、Token & 成本\n")
    lines.append("| 模型 | 调用次数 | 总 tokens | 估算成本(元) | 平均延迟(ms) |")
    lines.append("|------|----------|-----------|---------------|--------------|")
    for model, info in usage.get("by_model", {}).items():
        lines.append(f"| {model} | {info['calls']} | {info['tokens']} | "
                     f"{info['cost']:.4f} | {int(info['latency_ms']/max(1,info['calls']))} |")

    lines.append("\n## 三、明细\n")
    for r in records:
        lines.append(f"\n### {r['req_id']} - {r['req_name']}  （模型：{r['model']}）")
        lines.append(f"- 生成用例数：{r['case_count']}")
        lines.append(f"- 字段完整率：{r['field_completeness']:.2%}")
        lines.append(f"- 优先级分布：{r['priority_dist']}")
        lines.append(f"- 自评通过：{r['self_review_passed']}/{r['self_review_total']}  ({r['self_review_rate']:.2%})")
        lines.append(f"- 自检覆盖率：{r['coverage_pct']}%")
        lines.append(f"- 耗时：{r['elapsed_sec']} s")
        if r["error"]:
            lines.append(f"- 异常：{r['error']}")

    lines.append("\n## 四、结论与建议\n")
    if "deepseek-v4-pro" in summary and "MiniMax-M3" in summary:
        d = summary["deepseek-v4-pro"]
        m = summary["MiniMax-M3"]
        winner = []
        for k in ["平均生成用例数", "平均字段完整率", "平均自评通过率",
                  "平均覆盖率(自检)"]:
            if d[k] > m[k]:
                winner.append(f"DeepSeek 在【{k}】上更优（{d[k]} vs {m[k]}）")
            elif m[k] > d[k]:
                winner.append(f"M3 在【{k}】上更优（{m[k]} vs {d[k]}）")
        # 成本优势
        ds_cost = usage["by_model"].get("deepseek-v4-pro", {}).get("cost", 0)
        m3_cost = usage["by_model"].get("MiniMax-M3", {}).get("cost", 0)
        if ds_cost and m3_cost:
            ratio = round(m3_cost / ds_cost, 2)
            winner.append(f"成本对比：DeepSeek {ds_cost:.4f} 元 vs M3 {m3_cost:.4f} 元（M3 是 DeepSeek 的 {ratio} 倍）")
        for w in winner:
            lines.append(f"- {w}")
        lines.append("\n**建议**：在【用例生成 / 评审 / 覆盖率检查】节点使用 DeepSeek-V4-Pro；"
                     "在【RAG 中文检索 / 需求结构化拆解】节点使用 MiniMax-M3。")

    return "\n".join(lines)


# ============================主入口==========================
def main():
    parser = argparse.ArgumentParser(description="用例生成能力对比：DeepSeek vs M3")
    parser.add_argument("--dataset", type=str, default=None,
                        help="评测集 JSON 路径（list of {id,name,text}）")
    parser.add_argument("--models", nargs="+", default=["deepseek-v4-pro", "MiniMax-M3"],
                        help="参与对比的模型 key 列表")
    parser.add_argument("--rounds", type=int, default=1,
                        help="每份需求跑几轮（默认 1，结果取最后一次）")
    parser.add_argument("--report", choices=["json", "md", "both"], default="both",
                        help="输出报告格式")
    parser.add_argument("--out-dir", type=str, default=os.path.join(SCRIPT_DIR, "eval_dataset", "results"),
                        help="报告输出目录")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    # 1) 加载评测集
    if args.dataset:
        with open(args.dataset, "r", encoding="utf-8") as f:
            requirements = json.load(f)
    elif os.path.exists(DEFAULT_DATASET_PATH):
        with open(DEFAULT_DATASET_PATH, "r", encoding="utf-8") as f:
            requirements = json.load(f)
    else:
        requirements = DEFAULT_REQUIREMENTS
        # 顺手落盘一份，下次直接用
        with open(DEFAULT_DATASET_PATH, "w", encoding="utf-8") as f:
            json.dump(requirements, f, ensure_ascii=False, indent=2)
        print(f"[init] 默认评测集已写入 {DEFAULT_DATASET_PATH}")

    print(f"评测集：{len(requirements)} 份需求")
    print(f"参与模型：{args.models}")
    print(f"每份需求跑 {args.rounds} 轮\n")

    # 2) 把所有节点路由清回默认，避免上一次实验污染
    reset_routing()

    # 3) 跑每对 (模型, 需求)
    records: List[Dict[str, Any]] = []
    for model_key in args.models:
        # 把"用例生成 + 评审 + 覆盖"全切到同一模型
        for t in [TaskType.CASE_GENERATION, TaskType.CASE_REVIEW, TaskType.COVERAGE_CHECK]:
            set_routing(t, model_key)
        llm = get_llm_for_task(TaskType.CASE_GENERATION)
        print(f"\n========== 模型：{llm.model_name} ==========")
        for req in requirements:
            for r in range(args.rounds):
                tag = f" [第{r+1}轮]" if args.rounds > 1 else ""
                print(f"\n--- {req['id']}{tag} ---")
                # 跑前清空本轮 usage 中属于"旧模型"的污染
                # （简单做法：每次新建一份 records；USAGE_HISTORY 会在最后统计时整体用）
                rec = run_one(llm, req)
                rec["round"] = r + 1
                records.append(rec)

    # 4) 汇总
    summary = aggregate(records)
    usage = get_usage_summary()

    print("\n\n=========== 汇总对比 ===========")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("\n=========== 用量 ===========")
    print(json.dumps(usage, ensure_ascii=False, indent=2))

    # 5) 输出报告
    ts = time.strftime("%Y%m%d_%H%M%S")
    if args.report in ("json", "both"):
        json_path = os.path.join(args.out_dir, f"comparison_{ts}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({"records": records, "summary": summary, "usage": usage},
                      f, ensure_ascii=False, indent=2)
        print(f"\n[报告] JSON 已写入 {json_path}")
        # 用量原始数据
        export_usage_history(os.path.join(args.out_dir, f"usage_{ts}.json"))

    if args.report in ("md", "both"):
        md_path = os.path.join(args.out_dir, f"comparison_{ts}.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(to_markdown(records, summary, usage))
        print(f"[报告] Markdown 已写入 {md_path}")


if __name__ == "__main__":
    main()
