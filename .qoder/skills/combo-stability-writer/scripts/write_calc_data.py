#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""组合稳定性分布 · 指标计算器数据写入工具

从 algorithmRetrospectiveCombinations.json 报文中提取指定模型组合的数据，
按需求口径计算每日排名、换算万元后写入指标计算器 Excel 的 A16:E47 数据区：
  A列=日期  B列=每日排名r  C列=策略收益(万)  D列=实际收益(万)  E列=有效天标志(公式重建)

口径基准（用户确认 + spot_review.js 代码验证）：
  有效天   = 当日策略收益≠0且非空 且 该日实际收益数据存在
             （考核数据与实际收益数据是两套数据，但存在性判定等价，以实际收益是否存在判定）
  每日排名 = 当日参与组合按策略收益降序稳定排序，名次=位置序号，并列按报文顺序取相邻名次
             参与口径与有效天一致（需求口径）；--rank-mode frontend 复现 847 行缺陷行为
  覆盖率   = validDays ÷ 区间天数D，D=len(dailyDataList)，不可用 len(actualBaseline)
  胜率     = winDays ÷ validDays，胜天 = 当日策略收益 > 当日实际收益（跑赢实际）
"""
import argparse
import json
import math
import sys
from pathlib import Path

import openpyxl
from openpyxl.styles import PatternFill

DATA_START = 17          # 数据区起始行
DATA_MAX_ROWS = 31       # 计算器容量（17~47）
INVALID_FILL = PatternFill('solid', fgColor='FFF2CC')
NO_FILL = PatternFill(fill_type=None)
E_FORMULA = '=IF(AND(B{r}<>"",C{r}<>"",C{r}<>0,D{r}<>""),1,0)'


def find_project_root() -> Path:
    """从脚本位置向上找含 .qoder 目录的祖先作为项目根。"""
    for anc in Path(__file__).resolve().parents:
        if (anc / '.qoder').is_dir():
            return anc
    return Path.cwd()


def sp_of(combo, dt):
    """组合在指定日期的 strategyProfit；键缺失或值为 null 均返回 None。"""
    return next((dd.get('strategyProfit') for dd in combo['dailyDataList'] if dd['date'] == dt), None)


def daily_ranks(combos, base, ti, dates, mode):
    """计算目标组合每日排名。返回 {date: rank}。

    requirement：当日策略收益非零非空 且 当日有实际收益才参与（需求口径=有效天口径）
    frontend   ：仅策略收益非零非空即参与（复现 spot_review.js:847 缺陷，不查实际收益）
    排序规则对齐前端 849-852 行：降序稳定排序，名次=位置序号，并列按报文顺序取相邻名次。
    """
    ranks = {}
    for dt in dates:
        if sp_of(combos[ti], dt) in (None, 0):
            continue
        if mode == 'requirement' and dt not in base:
            continue
        part = [(i, sp_of(c, dt)) for i, c in enumerate(combos) if sp_of(c, dt) not in (None, 0)]
        part.sort(key=lambda x: (-x[1], x[0]))
        ranks[dt] = next(ri + 1 for ri, (i, _) in enumerate(part) if i == ti)
    return ranks


def invalid_reason(combo, base, dt):
    """无效天归因：None=有效天；否则返回类型描述。"""
    sp = sp_of(combo, dt)
    if sp is None:
        return '策略收益键缺失'
    if sp == 0:
        return '策略收益=0'
    if dt not in base:
        return '实际收益缺失'
    return None


def main():
    ap = argparse.ArgumentParser(description='组合稳定性分布·指标计算器数据写入')
    ap.add_argument('--json', default=None, help='报文路径')
    ap.add_argument('--excel', default=None, help='计算器Excel路径')
    ap.add_argument('--combo', default=None, help='目标组合label，缺省自动选validDays最高者')
    ap.add_argument('--rank-mode', choices=['requirement', 'frontend'], default='requirement',
                    help='排名口径：requirement=有效天参与(默认)；frontend=复现前端847行缺陷')
    ap.add_argument('--list', action='store_true', help='仅列出组合摘要，不写Excel')
    ap.add_argument('--dry-run', action='store_true', help='只计算与校验，不写Excel')
    ap.add_argument('--top', type=int, default=20, help='--list显示条数')
    args = ap.parse_args()

    root = find_project_root()
    json_path = Path(args.json) if args.json else root / '.qoder' / 'picture' / 'algorithmRetrospectiveCombinations.json'
    excel_path = Path(args.excel) if args.excel else root / '.qoder' / 'output' / 'aiAutoTester' / '组合稳定性分布' / '组合稳定性分布_指标计算器.xlsx'

    # ---- 1. 读取报文 ----
    try:
        payload = json.loads(json_path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        sys.exit(f'[ERROR] 报文不存在: {json_path}')
    model = payload.get('model') or payload
    combos = model.get('combinations') or []
    base = {x['date']: x['actualProfit'] for x in model.get('actualBaseline') or []}
    if not combos:
        sys.exit('[ERROR] 报文中无 combinations 数据')

    # ---- 2. --list 模式 ----
    if args.list:
        rows = sorted(enumerate(combos), key=lambda x: -x[1]['validDays'])[:args.top]
        print(f'共 {len(combos)} 个组合（按 validDays 降序前 {len(rows)}）：')
        print(f"{'validDays':>9} {'winDays':>7} {'winRate':>8} {'coverage':>9}  label")
        for _, c in rows:
            print(f"{c['validDays']:>9} {c['winDays']:>7} {c['winRate']:>8.4f} {c['coverage']:>9.4f}  {c['label']}")
        return

    # ---- 3. 选定目标组合 ----
    if args.combo:
        ti = next((i for i, c in enumerate(combos) if c['label'] == args.combo), None)
        if ti is None:
            sys.exit(f"[ERROR] 未找到组合: {args.combo}\n提示: 用 --list 查看可用组合 label")
    else:
        ti = max(range(len(combos)), key=lambda i: combos[i]['validDays'])
    target = combos[ti]
    dates = [dd['date'] for dd in target['dailyDataList']]
    n = len(dates)
    if n > DATA_MAX_ROWS:
        sys.exit(f'[ERROR] dailyDataList 长度 {n} 超过计算器容量 {DATA_MAX_ROWS} 行')

    # ---- 4. 计算排名与指标 ----
    ranks = daily_ranks(combos, base, ti, dates, args.rank_mode)
    valid_days = [dt for dt in dates if invalid_reason(target, base, dt) is None]
    t = len(valid_days)
    w = sum(1 for dt in valid_days if sp_of(target, dt) > base[dt])
    win_rate, coverage = (w / t if t else 0), (t / n if n else 0)

    # ---- 5. 与报文交叉校验 ----
    print('=' * 62)
    print(f"目标组合: {target['label']}")
    print(f"区间: {dates[0]} ~ {dates[-1]}  D=len(dailyDataList)={n}  A=len(actualBaseline)={len(base)}")
    print(f"排名口径: {'requirement(有效天参与)' if args.rank_mode == 'requirement' else 'frontend(复现847行缺陷,仅B列对比)'}")
    print('-' * 62)
    checks = [
        ('有效天数 T', t, target['validDays'], 0),
        ('胜天数 W', w, target['winDays'], 0),
        ('胜率', round(win_rate, 4), round(target['winRate'], 4), 5e-5),
        ('覆盖率', round(coverage, 4), round(target['coverage'], 4), 5e-5),
    ]
    ok = True
    for name, got, exp, tol in checks:
        match = abs(got - exp) <= tol
        ok &= match
        print(f"  {name:<8} 计算={got:<10} 报文={exp:<10} {'PASS' if match else 'FAIL'}")
    if not ok:
        sys.exit('[ERROR] 交叉校验失败，终止写入（请检查报文口径是否变化）')

    rs = [ranks[dt] for dt in valid_days if dt in ranks]
    if rs:
        mu = sum(rs) / len(rs)
        sd = math.sqrt(sum((x - mu) ** 2 for x in rs) / len(rs))
        topk = max(1, math.ceil(len(combos) * 0.1))
        print(f"  预计算(报文无此字段): μ={mu:.1f} σ={sd:.1f} 前10%率={sum(1 for x in rs if x <= topk)/len(rs)*100:.1f}% "
              f"爆雷率={sum(1 for x in rs if x > len(combos)-topk)/len(rs)*100:.1f}% LCB={mu+sd/math.sqrt(len(rs)):.1f}")
    invalids = [(dt, invalid_reason(target, base, dt)) for dt in dates if invalid_reason(target, base, dt)]
    print(f"  无效天 {len(invalids)} 个: " + ('; '.join(f'{d}({r})' for d, r in invalids) if invalids else '无'))
    print('=' * 62)
    if args.dry_run:
        print('[DRY-RUN] 校验通过，未写入 Excel')
        return

    # ---- 6. 写入 Excel ----
    try:
        wb = openpyxl.load_workbook(excel_path)
    except FileNotFoundError:
        sys.exit(f'[ERROR] 计算器不存在: {excel_path}')
    ws = wb.active
    for i, dt in enumerate(dates):
        r = DATA_START + i
        sp, ap = sp_of(target, dt), base.get(dt)
        ws.cell(row=r, column=1).value = dt                       # A 日期
        ws.cell(row=r, column=2).value = ranks.get(dt)            # B 每日排名(无效天=None清空)
        c3 = ws.cell(row=r, column=3)                             # C 策略收益(万)
        c3.value = None if sp is None else round(sp / 10000, 6)
        c3.number_format = '0.0000'
        c4 = ws.cell(row=r, column=4)                             # D 实际收益(万)
        c4.value = None if ap is None else round(ap / 10000, 6)
        c4.number_format = '0.0000'
    # 清空超出 n 的旧行（openpyxl 陷阱：cell(value=None) 不清空，必须 .value=None）
    for r in range(DATA_START + n, DATA_START + DATA_MAX_ROWS):
        for col in range(1, 5):
            ws.cell(row=r, column=col).value = None
        ws.cell(row=r, column=3).number_format = '0.0000'
        ws.cell(row=r, column=4).number_format = '0.0000'
    # E 列公式重建 + 高亮重置（先全清，再对无效天行高亮）
    for r in range(DATA_START, DATA_START + DATA_MAX_ROWS):
        ws.cell(row=r, column=5).value = E_FORMULA.format(r=r)
        for col in range(1, 6):
            ws.cell(row=r, column=col).fill = NO_FILL
    hl_rows = [DATA_START + i for i, dt in enumerate(dates) if invalid_reason(target, base, dt)]
    for r in hl_rows:
        for col in range(1, 6):
            ws.cell(row=r, column=col).fill = INVALID_FILL
    ws['B4'] = n                                                  # 区间天数 D 同步
    # 口径说明区动态更新（第3/4/8条，行号依赖计算器模板结构）
    if ws['A49'].value == '口径说明':
        ws['A52'] = ('3. 无效天示例(高亮行%s)：%s' % (
            f'{hl_rows[0]}-{hl_rows[-1]}' if len(hl_rows) > 1 else (hl_rows[0] if hl_rows else '无'),
            '；'.join(f'{d}({r})' for d, r in invalids) if invalids else '本组合无无效天'))
        ws['A53'] = (f'4. 区间天数D(B4)=len(dailyDataList)={n}，覆盖率分母=D；本表有实际收益的天数A={len(base)}'
                     + (f'，若误用A做分母覆盖率虚高为{t}/{len(base)}={t/len(base)*100:.1f}%(正确值{coverage*100:.1f}%)'
                        if len(base) < n else '，本区间D=A无缺实际收益日'))
        ws['A57'] = (f'8. 本表A-D列取自真实报文组合“{target["label"]}”({dates[0]}~{dates[-1]})，'
                     f'C/D列=报文原值÷10000(单位:万)；B列每日排名按{args.rank_mode}口径计算'
                     f'(当日收益降序、并列按报文顺序取相邻名次)；报文基准validDays={target["validDays"]}'
                     f'/winDays={target["winDays"]}/winRate={target["winRate"]:.4f}/coverage={target["coverage"]:.4f}')
    try:
        wb.save(excel_path)
    except PermissionError:
        sys.exit(f'[ERROR] Excel 文件被占用，请先关闭后重试: {excel_path}')
    print(f'已写入 {excel_path}')
    print(f'高亮无效天行: {hl_rows if hl_rows else "无"} | B4 已同步为 {n} | E列公式已重建')

    # ---- 7. 落盘回读校验 ----
    wb2 = openpyxl.load_workbook(excel_path)
    ws2 = wb2.active
    bad = []
    for i, dt in enumerate(dates):
        r = DATA_START + i
        got = tuple(ws2.cell(row=r, column=j).value for j in (2, 3, 4))
        exp = (ranks.get(dt),
               None if sp_of(target, dt) is None else round(sp_of(target, dt) / 10000, 6),
               None if base.get(dt) is None else round(base[dt] / 10000, 6))
        if got != exp:
            bad.append((dt, got, exp))
    sim_t = sum(1 for i, dt in enumerate(dates)
                if all(ws2.cell(row=DATA_START + i, column=j).value not in (None, '')
                       for j in (2, 4))
                and ws2.cell(row=DATA_START + i, column=3).value not in (None, '', 0))
    print(f'落盘校验: B/C/D 31行内比对 {"PASS" if not bad else bad} | 模拟E列T={sim_t} (应{t}) '
          f'{"PASS" if sim_t == t else "FAIL"}')
    if bad or sim_t != t:
        sys.exit(1)
    print('全部完成 ✔')


if __name__ == '__main__':
    main()
