#!/usr/bin/env python3
"""Extract numeric fields from a JSON array and compute sums."""

import argparse
import json
import sys
import os


def sum_field(data, field, time_field="time"):
    values = []
    for item in data:
        if field not in item:
            continue
        values.append({
            "label": item.get(time_field, item.get("time", "N/A")),
            "value": item[field]
        })
    return values


def main():
    parser = argparse.ArgumentParser(description="Sum numeric fields from JSON array data")
    parser.add_argument("--input", required=True, help="JSON file path or inline JSON string")
    parser.add_argument("--field", default=None, help="Single field name to sum")
    parser.add_argument("--fields", default=None, help="Comma-separated field names to sum")
    parser.add_argument("--profit", action="store_true", help="Auto-sum arbitrageProfits and strategyProfit")
    parser.add_argument("--time-field", default="time", help="Field name for time/label column (default: time)")
    args = parser.parse_args()

    input_str = args.input.strip()

    # Determine if input is a file path or inline JSON
    normalized = os.path.normpath(input_str)
    if os.path.isfile(normalized):
        with open(normalized, "r", encoding="utf-8") as f:
            data = json.load(f)
    elif input_str.startswith("["):
        data = json.loads(input_str)
    else:
        print(f"Error: cannot read file '{input_str}' and input does not look like JSON", file=sys.stderr)
        sys.exit(1)

    if not isinstance(data, list):
        print("Error: input must be a JSON array", file=sys.stderr)
        sys.exit(1)

    # Determine which fields to sum
    if args.profit:
        fields = ["arbitrageProfits", "strategyProfit"]
    elif args.fields:
        fields = [f.strip() for f in args.fields.split(",")]
    elif args.field:
        fields = [args.field]
    else:
        fields = ["strategyProfit"]

    count = len(data)

    for field in fields:
        values = sum_field(data, field, args.time_field)
        if not values:
            print(f"未找到字段 '{field}'")
            continue

        total = sum(v["value"] for v in values)
        print(f"{field} 总和: {total:.4f}（共 {count} 条记录）")


if __name__ == "__main__":
    main()
