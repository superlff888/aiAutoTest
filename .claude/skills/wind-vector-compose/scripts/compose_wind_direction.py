#!/usr/bin/env python3
"""多采样点风向/风速时序向量合成。

对每个时刻（下标），将该时刻所有采样点的风向按风速加权分解为二维向量并求和，
再用 atan2 还原为综合风向（0~360 度）。

气象约定：0° = 正北，顺时针增大；故 x 取 sin（东向分量），y 取 cos（北向分量），
还原角度使用 atan2(x, y)（注意参数顺序），并对 360 取模归一。
"""

import argparse
import json
import math
import os
import sys


def compose_direction(speeds_by_station, directions_by_station, round_digits=2):
    """按“同一时刻、跨采样点”做风速加权向量合成。

    Args:
        speeds_by_station: List[List[float]]，每个子列表是一个采样点的时序风速。
        directions_by_station: List[List[float]]，结构与上相同，单位为度。
        round_digits: 结果保留的小数位数。

    Returns:
        List[float]：每个时刻的综合风向（0~360 度）。
    """
    n_stations = len(speeds_by_station)
    if n_stations == 0:
        raise ValueError("采样点数量为 0，无法计算")
    if len(directions_by_station) != n_stations:
        raise ValueError(
            f"风速数组数量({n_stations})与风向数组数量({len(directions_by_station)})不一致"
        )

    n_times = len(speeds_by_station[0])
    for idx, (sp, dr) in enumerate(zip(speeds_by_station, directions_by_station), start=1):
        if len(sp) != n_times or len(dr) != n_times:
            raise ValueError(
                f"编号{idx}的数组长度({len(sp)}/{len(dr)})与首个数组长度({n_times})不一致"
            )

    result = []
    for t in range(n_times):
        x = 0.0  # 东向分量
        y = 0.0  # 北向分量
        for i in range(n_stations):
            v = speeds_by_station[i][t]
            rad = math.radians(directions_by_station[i][t])
            x += v * math.sin(rad)
            y += v * math.cos(rad)
        angle = math.degrees(math.atan2(x, y)) % 360
        result.append(round(angle, round_digits))
    return result


def _load_json(text):
    """text 可以是 JSON 文件路径，也可以是内联 JSON 字符串。"""
    text = text.strip()
    normalized = os.path.normpath(text)
    if os.path.isfile(normalized):
        with open(normalized, "r", encoding="utf-8") as f:
            return json.load(f)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        print(f"Error: 无法解析 JSON 输入：{exc}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="多采样点风向/风速时序向量合成，输出各时刻综合风向"
    )
    parser.add_argument(
        "--input",
        default=None,
        help='JSON 文件路径或内联 JSON，格式 {"speeds":[[...]], "directions":[[...]]}',
    )
    parser.add_argument(
        "--speeds", default=None, help="风速数组的 JSON（文件路径或内联），二维数组"
    )
    parser.add_argument(
        "--directions", default=None, help="风向数组的 JSON（文件路径或内联），二维数组"
    )
    parser.add_argument(
        "--round", type=int, default=2, dest="round_digits", help="结果保留小数位，默认 2"
    )
    parser.add_argument(
        "--consistency",
        action="store_true",
        help="额外输出各时刻方向一致性（合成向量长度 / 风速总和）",
    )
    args = parser.parse_args()

    speeds = directions = None
    if args.input:
        payload = _load_json(args.input)
        if not isinstance(payload, dict) or "speeds" not in payload or "directions" not in payload:
            print('Error: --input 需为含 "speeds" 与 "directions" 键的 JSON 对象', file=sys.stderr)
            sys.exit(1)
        speeds = payload["speeds"]
        directions = payload["directions"]
    elif args.speeds and args.directions:
        speeds = _load_json(args.speeds)
        directions = _load_json(args.directions)
    else:
        print("Error: 请提供 --input，或同时提供 --speeds 与 --directions", file=sys.stderr)
        sys.exit(1)

    try:
        result = compose_direction(speeds, directions, args.round_digits)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"综合风向数组（共 {len(result)} 个时刻，单位：度）：")
    print(result)

    if args.consistency:
        n_times = len(result)
        ratios = []
        for t in range(n_times):
            x = sum(
                speeds[i][t] * math.sin(math.radians(directions[i][t]))
                for i in range(len(speeds))
            )
            y = sum(
                speeds[i][t] * math.cos(math.radians(directions[i][t]))
                for i in range(len(speeds))
            )
            total_speed = sum(speeds[i][t] for i in range(len(speeds)))
            ratio = (math.hypot(x, y) / total_speed) if total_speed else 0.0
            ratios.append(round(ratio, 3))
        print("方向一致性（合成向量长度 / 风速总和，越接近 1 越一致）：")
        print(ratios)


if __name__ == "__main__":
    main()
