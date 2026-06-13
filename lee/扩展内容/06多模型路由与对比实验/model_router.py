# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee/06多模型路由与对比实验/model_router.py
# @Author      : Lee大侠
# @Desc        : 多模型路由——按"任务类型"自动选择底层 LLM
# @CreateTime  : 2026/06/07
# @UpdateTime  : 2026/06/07
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================

"""
多模型路由（Model Router）
================================

# 设计目标
    把"用什么模型"和"做什么任务"解耦：
        - 上层业务（用例生成 / 评审 / 覆盖率 / RAG）只声明"我要做啥"
        - 路由层根据预设策略自动选模型（DeepSeek / M3 / 其它）
        - 一处改动，全局生效；切换模型 / 调价 / A/B 实验都不用改业务代码

# 路由策略（默认）
    +----------------------+----------------+-----------------------------+
    | 任务类型             | 主选模型       | 备选 / 备注                 |
    +----------------------+----------------+-----------------------------+
    | CASE_GENERATION      | deepseek-v4-pro | 推理强、生成结构稳、价格低  |
    | CASE_SUPPLEMENT      | deepseek-v4-pro | 补充生成走同一类模型        |
    | CASE_REVIEW          | deepseek-v4-pro | 评审需要严格判等/规则      |
    | COVERAGE_CHECK       | deepseek-v4-pro | 逻辑判断密集                |
    | STRUCTURED_EXTRACT   | deepseek-v4-pro | 长 JSON 抽取稳定            |
    | RAG_QUERY            | MiniMax-M3     | 中文语义理解细腻            |
    | RAG_RERANK           | MiniMax-M3     | 文档/需求阅读更细腻         |
    | SIMPLE_CHAT          | MiniMax-M3     | 闲聊/兜底                   |
    +----------------------+----------------+-----------------------------+

# 使用方式
    from model_router import get_llm_for_task, TaskType

    llm = get_llm_for_task(TaskType.CASE_GENERATION)
    resp = llm.invoke(prompt)
"""

from __future__ import annotations

import os
import time
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from typing import Any, Dict, List, Optional

import dotenv
from langchain_openai.chat_models import ChatOpenAI

# ============================全局环境==========================
# 加载根目录的 .env（与原项目保持一致）
dotenv.load_dotenv(dotenv.find_dotenv())

logging.basicConfig(
    level=os.getenv("ROUTER_LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s :: %(message)s",
)
log = logging.getLogger("model_router")


# ============================任务类型==========================
class TaskType(str, Enum):
    """用例生成工作流中所有可能的任务节点。"""
    # 主流程
    CASE_GENERATION = "case_generation"           # 初次生成用例
    CASE_SUPPLEMENT = "case_supplement"           # 补充生成用例
    CASE_REVIEW = "case_review"                   # 单条用例评审
    COVERAGE_CHECK = "coverage_check"             # 覆盖率检查
    STRUCTURED_EXTRACT = "structured_extract"     # 结构化抽取（JSON）

    # RAG / 知识库
    RAG_QUERY = "rag_query"                       # RAG 检索 + 问答
    RAG_RERANK = "rag_rerank"                     # 检索结果重排
    REQUIREMENT_PARSE = "requirement_parse"       # 需求结构化拆解

    # 通用
    SIMPLE_CHAT = "simple_chat"                   # 闲聊 / 兜底
    CODE_GEN = "code_gen"                         # 代码生成/补全


# ============================模型档案==========================
@dataclass
class ModelProfile:
    """
    单个模型的"档案卡"：包含调用所需的所有参数 + 计费参考。
    """
    name: str                          # 模型名（API 侧 model 字段）
    display_name: str                  # 给人看的名字
    base_url: str                      # OpenAI 兼容 base_url
    api_key: str                       # API Key
    temperature: float = 0.5
    max_tokens: int = 4096
    timeout: int = 60
    # 计费参考（元 / 1k tokens）；如未知填 0
    price_input: float = 0.0
    price_output: float = 0.0
    # 备注
    note: str = ""


# ============================路由配置==========================
# 这里集中维护"每个任务 → 用哪个模型"。
# 改这里一行就能切换 A/B 实验。
DEFAULT_ROUTING: Dict[TaskType, str] = {
    # —— 推理/逻辑密集 → DeepSeek ——
    TaskType.CASE_GENERATION: "deepseek-v4-pro",
    TaskType.CASE_SUPPLEMENT: "deepseek-v4-pro",
    TaskType.CASE_REVIEW: "deepseek-v4-pro",
    TaskType.COVERAGE_CHECK: "deepseek-v4-pro",
    TaskType.STRUCTURED_EXTRACT: "deepseek-v4-pro",
    TaskType.CODE_GEN: "deepseek-v4-pro",

    # —— 中文语义/细腻度 → M3 ——
    TaskType.RAG_QUERY: "MiniMax-M3",
    TaskType.RAG_RERANK: "MiniMax-M3",
    TaskType.REQUIREMENT_PARSE: "MiniMax-M3",

    # —— 兜底 ——
    TaskType.SIMPLE_CHAT: "MiniMax-M3",
}


# ============================模型注册表==========================
# 真实可用的两套模型；从环境变量读取，缺省有 fallback。
def _build_profiles() -> Dict[str, ModelProfile]:
    """从 .env 构建模型档案表。"""
    profiles: Dict[str, ModelProfile] = {}

    # 1) DeepSeek（v4-pro）
    ds_key = os.getenv("DS_API_KEY")
    ds_url = os.getenv("DS_BASE_URL", "https://api.deepseek.com")
    ds_model = os.getenv("DS_MODEL", "deepseek-v4-pro")
    if ds_key:
        profiles["deepseek-v4-pro"] = ModelProfile(
            name=ds_model,
            display_name="DeepSeek-V4-Pro",
            base_url=ds_url,
            api_key=ds_key,
            temperature=0.3,            # 推理/生成场景：低温更稳
            max_tokens=8192,
            timeout=120,
            price_input=0.001,          # 元/1k tokens（参考价，按需改）
            price_output=0.002,
            note="推理强、价格低、长上下文；用例生成/评审主选",
        )

    # 2) MiniMax-M3
    m3_key = os.getenv("OPENAI_API_KEY")
    m3_url = os.getenv("OPENAI_BASE_URL", "https://api.minimaxi.com/v1")
    m3_model = os.getenv("OPENAI_MODEL", "MiniMax-M3")
    if m3_key:
        profiles["MiniMax-M3"] = ModelProfile(
            name=m3_model,
            display_name="MiniMax-M3",
            base_url=m3_url,
            api_key=m3_key,
            temperature=0.5,
            max_tokens=4096,
            timeout=60,
            price_input=0.01,           # 元/1k tokens（参考价，按需改）
            price_output=0.03,
            note="中文细腻度高、风格自然；RAG/中文语义首选",
        )

    return profiles


# 全局单例
PROFILES: Dict[str, ModelProfile] = _build_profiles()
ROUTING: Dict[TaskType, str] = dict(DEFAULT_ROUTING)


# ============================用量统计==========================
@dataclass
class UsageRecord:
    task: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    latency_ms: int = 0
    timestamp: float = field(default_factory=time.time)


USAGE_HISTORY: List[UsageRecord] = []


def _record_usage(task: TaskType, profile: ModelProfile,
                  resp: Any, latency_ms: int) -> None:
    """从 ChatOpenAI 返回值里抓 token 用量并累计。"""
    try:
        usage = getattr(resp, "response_metadata", {}).get("token_usage", {}) \
                or getattr(resp, "usage_metadata", {}) \
                or {}
        p_t = int(usage.get("prompt_tokens", 0))
        c_t = int(usage.get("completion_tokens", 0))
        t_t = int(usage.get("total_tokens", p_t + c_t))
    except Exception:
        p_t = c_t = t_t = 0

    cost = (p_t / 1000.0) * profile.price_input + (c_t / 1000.0) * profile.price_output

    USAGE_HISTORY.append(UsageRecord(
        task=task.value,
        model=profile.name,
        prompt_tokens=p_t,
        completion_tokens=c_t,
        total_tokens=t_t,
        cost=round(cost, 6),
        latency_ms=latency_ms,
    ))


# ============================对外接口==========================
def get_profile(model_key: str) -> ModelProfile:
    """根据模型 key 获取档案；找不到时返回 M3 作为兜底。"""
    if model_key in PROFILES:
        return PROFILES[model_key]
    log.warning("模型 %s 未注册，回退到 M3", model_key)
    if "MiniMax-M3" in PROFILES:
        return PROFILES["MiniMax-M3"]
    # 真一个都没有就用第一个
    return next(iter(PROFILES.values()))


def list_models() -> List[Dict[str, Any]]:
    """列出所有可用模型（给 CLI / Web 用）。"""
    return [
        {
            "key": k,
            "name": v.name,
            "display_name": v.display_name,
            "base_url": v.base_url,
            "temperature": v.temperature,
            "max_tokens": v.max_tokens,
            "note": v.note,
        }
        for k, v in PROFILES.items()
    ]


def list_routing() -> Dict[str, str]:
    """查看当前路由表。"""
    return {t.value: m for t, m in ROUTING.items()}


def set_routing(task: TaskType, model_key: str) -> None:
    """运行时改路由（供 A/B 实验 / 评测脚本用）。"""
    if model_key not in PROFILES:
        raise ValueError(f"未知模型 {model_key}，可选：{list(PROFILES.keys())}")
    ROUTING[task] = model_key
    log.info("路由已更新：%s -> %s", task.value, model_key)


def reset_routing() -> None:
    """重置回默认路由。"""
    ROUTING.clear()
    ROUTING.update(DEFAULT_ROUTING)


@lru_cache(maxsize=32)
def _cached_chat(profile_id: str, temperature: float, max_tokens: int) -> ChatOpenAI:
    """
    缓存 ChatOpenAI 实例。同 (model, temp, max_tokens) 复用同一对象，
    避免每次 new 一个连接。
    """
    for prof in PROFILES.values():
        if prof.name == profile_id:
            return ChatOpenAI(
                api_key=prof.api_key,
                base_url=prof.base_url,
                model=prof.name,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=prof.timeout,
            )
    raise ValueError(f"未找到模型档案 {profile_id}")


def get_llm_for_task(
    task: TaskType,
    *,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    track_usage: bool = True,
) -> ChatOpenAI:
    """
    主入口：按任务类型返回一个 ChatOpenAI 实例。
    用法：
        llm = get_llm_for_task(TaskType.CASE_GENERATION)
        resp = llm.invoke(prompt)
    """
    model_key = ROUTING.get(task)
    if not model_key:
        raise ValueError(f"任务 {task} 未配置路由，请先 set_routing()")

    prof = get_profile(model_key)
    temp = temperature if temperature is not None else prof.temperature
    mx = max_tokens if max_tokens is not None else prof.max_tokens

    log.debug("路由 %s -> %s (temp=%s, max_tokens=%s)",
              task.value, prof.name, temp, mx)

    if track_usage:
        return _TrackedChatOpenAI(prof, task, temp, mx)
    return _cached_chat(prof.name, temp, mx)


# ============================带用量追踪的 ChatOpenAI==========================
class _TrackedChatOpenAI(ChatOpenAI):
    """
    包装一层 ChatOpenAI：每次 invoke 后自动把 token 用量/耗时写入 USAGE_HISTORY。
    用法与 ChatOpenAI 完全一致。
    """
    def __init__(self, profile: ModelProfile, task: TaskType,
                 temperature: float, max_tokens: int):
        super().__init__(
            api_key=profile.api_key,
            base_url=profile.base_url,
            model=profile.name,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=profile.timeout,
        )
        self._profile = profile
        self._task = task

    def invoke(self, *args, **kwargs):  # type: ignore[override]
        t0 = time.time()
        resp = super().invoke(*args, **kwargs)
        _record_usage(self._task, self._profile, resp, int((time.time() - t0) * 1000))
        return resp

    async def ainvoke(self, *args, **kwargs):  # type: ignore[override]
        t0 = time.time()
        resp = await super().ainvoke(*args, **kwargs)
        _record_usage(self._task, self._profile, resp, int((time.time() - t0) * 1000))
        return resp


# ============================用量查询==========================
def get_usage_summary() -> Dict[str, Any]:
    """汇总当前进程的 token / 成本消耗。"""
    if not USAGE_HISTORY:
        return {"total_calls": 0, "total_tokens": 0, "total_cost": 0.0,
                "by_model": {}, "by_task": {}}

    by_model: Dict[str, Dict[str, int]] = {}
    by_task: Dict[str, Dict[str, int]] = {}

    total_tokens = 0
    total_cost = 0.0
    total_latency = 0

    for r in USAGE_HISTORY:
        total_tokens += r.total_tokens
        total_cost += r.cost
        total_latency += r.latency_ms

        m = by_model.setdefault(r.model, {"calls": 0, "tokens": 0, "cost": 0.0, "latency_ms": 0})
        m["calls"] += 1
        m["tokens"] += r.total_tokens
        m["cost"] += r.cost
        m["latency_ms"] += r.latency_ms

        t = by_task.setdefault(r.task, {"calls": 0, "tokens": 0, "cost": 0.0})
        t["calls"] += 1
        t["tokens"] += r.total_tokens
        t["cost"] += r.cost

    return {
        "total_calls": len(USAGE_HISTORY),
        "total_tokens": total_tokens,
        "total_cost": round(total_cost, 6),
        "avg_latency_ms": int(total_latency / max(1, len(USAGE_HISTORY))),
        "by_model": by_model,
        "by_task": by_task,
    }


def export_usage_history(path: str) -> None:
    """把用量历史落盘成 JSON（评测脚本会用）。"""
    data = [r.__dict__ for r in USAGE_HISTORY]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log.info("用量历史已写入 %s（共 %d 条）", path, len(data))


# ============================CLI 调试入口==========================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="多模型路由 CLI 调试")
    parser.add_argument("--list", action="store_true", help="列出所有模型 + 路由表")
    parser.add_argument("--summary", action="store_true", help="打印当前用量汇总")
    parser.add_argument("--export", type=str, default=None, help="导出用量历史到 JSON")
    parser.add_argument("--test", action="store_true", help="对每个任务做一次最小调用测试")
    args = parser.parse_args()

    if args.list:
        print("=" * 60)
        print("可用模型：")
        print("=" * 60)
        print(json.dumps(list_models(), ensure_ascii=False, indent=2))
        print("\n当前路由表：")
        print("=" * 60)
        print(json.dumps(list_routing(), ensure_ascii=False, indent=2))

    if args.summary:
        print("\n用量汇总：")
        print("=" * 60)
        print(json.dumps(get_usage_summary(), ensure_ascii=False, indent=2))

    if args.export:
        export_usage_history(args.export)

    if args.test:
        print("\n最小调用测试：")
        print("=" * 60)
        for task in TaskType:
            try:
                llm = get_llm_for_task(task)
                resp = llm.invoke("只回答一个字：好")
                print(f"[{task.value}] -> {llm.model_name} :: {resp.content[:30]!r}")
            except Exception as e:
                print(f"[{task.value}] 失败：{e}")
        print("\n用量汇总：")
        print(json.dumps(get_usage_summary(), ensure_ascii=False, indent=2))
