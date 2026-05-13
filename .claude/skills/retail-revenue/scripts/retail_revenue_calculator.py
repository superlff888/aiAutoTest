#!/usr/bin/env python3
"""
虚拟电厂零售侧收入计算器（海南交易中心）

计算链路（8步，严格按顺序，无循环依赖）：
1. 用户固定价格电费 = 实际用电量 × (1 - 联动比例) × 固定价格
2. 用户市场联动电费 = 实际用电量 × 联动比例 × 联动价格
3. 用户零售套餐电费 = 步骤1 + 步骤2
4. 用户电能量结算均价 = 步骤3 / 实际用电量
5. 用户风险管控费用（高价触发用110%限价，低价触发用90%限价）
6. 用户电量电费 = 步骤3 + 步骤5
7. 售电公司售电收益 = SUM(步骤6) - 批发侧成本；收益均价 = 售电收益 / 总用电量
8. 超额收益返还 & 用户零售侧收入
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass


@dataclass
class UserInput:
    name: str
    actual_consumption: float
    market_linkage_ratio: float
    fixed_price: float
    market_linkage_price: float


@dataclass
class UserResult:
    name: str
    cons: float
    fixed_elec: float
    linkage_elec: float
    package_elec: float
    settlement_price: float
    risk_fee: float
    risk_status: str  # "未触发" / "上限触发" / "下限触发"
    elec_fee: float
    user_excess: float
    retail_income: float


def parse_users(raw: list[dict]) -> list[UserInput]:
    """从 JSON 数据解析并校验用户输入"""
    required = {
        "name": str,
        "actual_consumption": (int, float),
        "market_linkage_ratio": (int, float),
        "fixed_price": (int, float),
        "market_linkage_price": (int, float),
    }
    users = []
    for i, item in enumerate(raw):
        missing = [k for k in required if k not in item]
        if missing:
            print(f"错误：用户 {i+1} 缺少字段 {missing}")
            sys.exit(1)
        for k, t in required.items():
            if not isinstance(item[k], t):
                print(f"错误：用户 {i+1} 字段 '{k}' 类型应为 {t}")
                sys.exit(1)
        users.append(UserInput(**item))
    return users


def extract_number(text: str) -> float:
    """从文本中提取数字，如 '352.26043元/MWh' -> 352.26043"""
    match = re.search(r"[-+]?\d*\.?\d+", text.strip())
    if match:
        return float(match.group())
    raise ValueError(f"无法从文本中提取数字: {text}")


def parse_text(text: str) -> tuple[float, float, list[UserInput]]:
    """从文本文档中解析基础数据

    支持的文本格式：
        1. 海南川量新能源科技有限公司：
        月度批发市场度电成本 	352.26043元/MWh
        批发侧成本	3909459.01507175元
        用户月度汇总实际用电量 64.8MWh
        市场联动价格比例	75%
        固定价格 325.000元/MWh
        市场联动价格	359.39000
    """
    # 按数字序号分割用户段落
    sections = re.split(r"\n\s*\d+\.", text)
    if not sections or all(s.strip() == "" for s in sections):
        print("错误：无法从文本中解析到用户数据，请检查格式")
        sys.exit(1)

    wholesale_cost = None
    wholesale_total_cost = None
    users_data: list[UserInput] = []

    for section in sections:
        section = section.strip()
        if not section:
            continue

        lines = section.split("\n")
        # 第一行是用户名称（去除序号前缀和末尾冒号）
        name = re.sub(r"^\d+\.\s*", "", lines[0].strip()).strip()
        name = name.rstrip("：").strip()
        if not name:
            continue

        user_data: dict[str, float] = {}
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue

            if "月度批发市场度电成本" in line:
                wholesale_cost = extract_number(line)
            elif "批发侧成本" in line:
                wholesale_total_cost = extract_number(line)
            elif "用户月度汇总实际用电量" in line:
                user_data["actual_consumption"] = extract_number(line)
            elif "市场联动价格比例" in line:
                val = extract_number(line)
                user_data["market_linkage_ratio"] = val / 100 if val > 1 else val
            elif "固定价格" in line:
                user_data["fixed_price"] = extract_number(line)
            elif "市场联动价格" in line and "比例" not in line:
                user_data["market_linkage_price"] = extract_number(line)

        if not all(k in user_data for k in ("actual_consumption", "market_linkage_ratio", "fixed_price", "market_linkage_price")):
            missing = [k for k in ("actual_consumption", "market_linkage_ratio", "fixed_price", "market_linkage_price") if k not in user_data]
            print(f"警告：用户 '{name}' 缺少字段 {missing}，跳过")
            continue

        users_data.append(UserInput(
            name=name,
            actual_consumption=user_data["actual_consumption"],
            market_linkage_ratio=user_data["market_linkage_ratio"],
            fixed_price=user_data["fixed_price"],
            market_linkage_price=user_data["market_linkage_price"],
        ))

    if not users_data:
        print("错误：未解析到任何有效用户数据")
        sys.exit(1)
    if wholesale_cost is None:
        print("错误：未找到「月度批发市场度电成本」")
        sys.exit(1)
    if wholesale_total_cost is None:
        print("错误：未找到「批发侧成本」")
        sys.exit(1)

    return wholesale_cost, wholesale_total_cost, users_data


def fmt(val, decimals: int = 2) -> str:
    """格式化数字"""
    if isinstance(val, bool):
        return "触发" if val else "未触发"
    if isinstance(val, float):
        return f"{val:,.{decimals}f}"
    return str(val)


def run_calculation(
    wholesale_cost: float,
    wholesale_total_cost: float,
    users_data: list[UserInput],
) -> tuple[list[UserResult], dict]:
    """执行完整计算，返回用户结果列表和汇总信息"""
    if not users_data:
        print("错误：用户数据为空")
        sys.exit(1)

    total_cons = sum(u.actual_consumption for u in users_data)

    # 步骤1-6：逐用户计算
    user_results: list[UserResult] = []
    for u in users_data:
        fixed_elec = u.actual_consumption * (1 - u.market_linkage_ratio) * u.fixed_price
        linkage_elec = u.actual_consumption * u.market_linkage_ratio * u.market_linkage_price
        package_elec = fixed_elec + linkage_elec
        settlement_price = package_elec / u.actual_consumption

        lower = wholesale_cost * 0.9
        upper = wholesale_cost * 1.1
        if lower <= settlement_price <= upper:
            risk_fee = 0.0
            risk_status = "未触发"
        elif settlement_price > upper:
            risk_fee = u.actual_consumption * (upper - settlement_price)
            risk_status = "上限触发"
        else:
            risk_fee = u.actual_consumption * (lower - settlement_price)
            risk_status = "下限触发"

        elec_fee = package_elec + risk_fee

        user_results.append(UserResult(
            name=u.name,
            cons=u.actual_consumption,
            fixed_elec=fixed_elec,
            linkage_elec=linkage_elec,
            package_elec=package_elec,
            settlement_price=settlement_price,
            risk_fee=risk_fee,
            risk_status=risk_status,
            elec_fee=elec_fee,
            user_excess=0.0,
            retail_income=0.0,
        ))

    # 步骤7：售电公司汇总
    company_revenue = sum(r.elec_fee for r in user_results) - wholesale_total_cost
    company_avg_price = company_revenue / total_cons

    # 步骤8：超额收益返还
    if company_avg_price > 15:
        company_excess = (company_avg_price - 15) * total_cons * 0.7
        excess_triggered = True
    else:
        company_excess = 0.0
        excess_triggered = False

    for r in user_results:
        r.user_excess = r.cons / total_cons * company_excess
        r.retail_income = r.package_elec + r.risk_fee - r.user_excess

    total_income = sum(r.retail_income for r in user_results)

    summary = {
        "wholesale_cost": wholesale_cost,
        "wholesale_total_cost": wholesale_total_cost,
        "total_cons": total_cons,
        "user_count": len(user_results),
        "company_revenue": company_revenue,
        "company_avg_price": company_avg_price,
        "company_excess": company_excess,
        "excess_triggered": excess_triggered,
        "total_income": total_income,
        "retail_per_mwh_revenue": total_income / total_cons,
    }

    return user_results, summary


def print_text_table(results: list[UserResult], summary: dict) -> None:
    """打印结果 — 10列固定格式，数值保留2位小数"""
    cols = ["用户", "用电量(MWh)", "固定价格电费", "市场联动电费", "零售套餐电费",
            "结算均价", "风险管控费用", "风险状态", "超额收益返还", "零售侧收入"]
    data = []
    for r in results:
        data.append([
            r.name,
            f"{r.cons:.2f}",
            f"{r.fixed_elec:.2f}",
            f"{r.linkage_elec:.2f}",
            f"{r.package_elec:.2f}",
            f"{r.settlement_price:.2f}",
            f"{r.risk_fee:.2f}",
            r.risk_status,
            f"{r.user_excess:.2f}",
            f"{r.retail_income:.2f}"
        ])

    widths = [len(c) for c in cols]
    for row in data:
        for i, v in enumerate(row):
            widths[i] = max(widths[i], len(str(v)))

    print(f"\n【基础参数】")
    print(f"  月度批发市场度电成本：{summary['wholesale_cost']:.8f} 元/MWh")
    print(f"  批发侧成本：{summary['wholesale_total_cost']:.8f} 元")
    print(f"  总用电量：{summary['total_cons']:.8f} MWh")
    print(f"  用户数：{summary['user_count']}")

    print(f"\n【用户维度明细】")
    header = " | ".join(c.ljust(widths[i]) for i, c in enumerate(cols))
    print(header)
    print("-" * len(header))
    for row in data:
        print(" | ".join(str(v).ljust(widths[i]) for i, v in enumerate(row)))

    print(f"\n【售电公司汇总】")
    print(f"  售电公司售电收益（扣除批发侧成本后）：{summary['company_revenue']:.2f} 元")
    print(f"  售电公司收益均价：{summary['company_avg_price']:.2f} 元/MWh")
    print(f"  零售侧度电收益：{summary['retail_per_mwh_revenue']:.2f} 元/MWh")
    print(f"  超额收益返还触发：{'是' if summary['excess_triggered'] else '否'}")
    if summary['excess_triggered']:
        print(f"  售电公司超额收益返还电费：{summary['company_excess']:.2f} 元")
        print(f"  返还比例：70%")

    print(f"\n【零售侧总收入】 {summary['total_income']:.2f} 元")


def print_json_output(results: list[UserResult], summary: dict) -> None:
    """打印 JSON 格式结果"""
    output = {
        "summary": summary,
        "users": [
            {
                "name": r.name,
                "cons": r.cons,
                "fixed_elec": round(r.fixed_elec, 2),
                "linkage_elec": round(r.linkage_elec, 2),
                "package_elec": round(r.package_elec, 2),
                "settlement_price": round(r.settlement_price, 2),
                "risk_fee": round(r.risk_fee, 2),
                "risk_status": r.risk_status,
                "elec_fee": round(r.elec_fee, 2),
                "user_excess": round(r.user_excess, 2),
                "retail_income": round(r.retail_income, 2),
            }
            for r in results
        ],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="虚拟电厂零售侧收入计算器（海南交易中心）")
    parser.add_argument("--wholesale-cost", type=float, help="月度批发市场度电成本（元/MWh）")
    parser.add_argument("--wholesale-total-cost", type=float, help="批发侧成本（元）")
    parser.add_argument("--users", type=str, help="用户数据 JSON 文件路径或内联 JSON 字符串")
    parser.add_argument("--text", type=str, help="文本文档路径或内联文本字符串，自动解析基础数据")
    parser.add_argument("--interactive", action="store_true", help="交互式输入模式")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出结果")

    args = parser.parse_args()

    if args.interactive:
        print("=== 虚拟电厂零售侧收入计算（交互模式） ===\n")
        wholesale_cost = float(input("请输入月度批发市场度电成本（元/MWh）："))
        wholesale_total_cost = float(input("请输入批发侧成本（元）："))

        users_data = []
        print("\n请输入用户数据（输入空用户名结束）：")
        idx = 1
        while True:
            name = input(f"\n用户{idx} 名称（回车结束）：").strip()
            if not name:
                break

            cons = float(input(f"  {name} - 月度汇总实际用电量(MWh)："))
            ratio = float(input(f"  {name} - 市场联动价格比例（如0.3表示30%）："))
            fixed_price = float(input(f"  {name} - 固定价格（元/MWh）："))
            market_price = float(input(f"  {name} - 市场联动价格（元/MWh）："))

            users_data.append(UserInput(
                name=name,
                actual_consumption=cons,
                market_linkage_ratio=ratio,
                fixed_price=fixed_price,
                market_linkage_price=market_price,
            ))
            idx += 1

        if not users_data:
            print("错误：未输入任何用户数据")
            sys.exit(1)

        if args.wholesale_cost is not None:
            wholesale_cost = args.wholesale_cost
        if args.wholesale_total_cost is not None:
            wholesale_total_cost = args.wholesale_total_cost

        results, summary = run_calculation(wholesale_cost, wholesale_total_cost, users_data)

    elif args.users:
        if args.wholesale_cost is None or args.wholesale_total_cost is None:
            print("错误：--wholesale-cost 和 --wholesale-total-cost 参数为必需")
            sys.exit(1)

        if os.path.isfile(args.users):
            with open(args.users, "r", encoding="utf-8") as f:
                raw = json.load(f)
        else:
            raw = json.loads(args.users)

        users_data = parse_users(raw)
        results, summary = run_calculation(args.wholesale_cost, args.wholesale_total_cost, users_data)

    elif args.text:
        # 文本文档解析模式
        if os.path.isfile(args.text):
            with open(args.text, "r", encoding="utf-8") as f:
                text_content = f.read()
        else:
            text_content = args.text

        wholesale_cost, wholesale_total_cost, users_data = parse_text(text_content)
        results, summary = run_calculation(wholesale_cost, wholesale_total_cost, users_data)

    else:
        parser.print_help()
        return

    if args.json:
        print_json_output(results, summary)
    else:
        print_text_table(results, summary)


if __name__ == "__main__":
    main()
