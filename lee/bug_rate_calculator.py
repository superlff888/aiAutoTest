"""
千行 Bug 率自动计算工具

自动扫描指定目录下所有代码文件的行数，结合 Bug 数量，计算千行 Bug 率。
公式：千行 Bug 率 = (Bug 数量 / 代码总行数) × 1000

Usage:
    python bug_rate_calculator.py                     # 默认扫描项目根目录，10 个 Bug
    python bug_rate_calculator.py --dir lee --bugs 10  # 指定目录和 Bug 数
    python bug_rate_calculator.py --detail             # 显示每个文件的明细
"""

import argparse
import os
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


# ===== 配置区 =====

# 支持的文件扩展名
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs",
    ".rb", ".sh", ".bash", ".php", ".c", ".cpp", ".h", ".cs",
}

# 排除的目录
EXCLUDE_DIRS = {
    ".git", ".venv", "venv", "__pycache__", "node_modules",
    ".idea", ".vscode", "build", "dist", ".tox",
}

# 注释标记（按语言）
COMMENT_MARKERS = {
    ".py": ("#", '"""', "'''"),
    ".js": ("//",),
    ".ts": ("//",),
    ".jsx": ("//",),
    ".tsx": ("//",),
    ".java": ("//",),
    ".go": ("//",),
    ".rs": ("//",),
    ".rb": ("#",),
    ".sh": ("#",),
    ".bash": ("#",),
    ".php": ("//", "#"),
    ".c": ("//",),
    ".cpp": ("//",),
    ".h": ("//",),
    ".cs": ("//",),
}


# ===== 数据类 =====

@dataclass
class FileStat:
    """单个文件的统计信息"""
    path: str
    total_lines: int = 0
    code_lines: int = 0       # 有效代码行（排除空行和纯注释）
    blank_lines: int = 0
    comment_lines: int = 0
    bug_count: int = 0
    bug_rate: float = 0.0     # 千行 Bug 率


@dataclass
class ModuleStat:
    """模块（目录）的统计信息"""
    name: str
    total_files: int = 0
    total_lines: int = 0
    code_lines: int = 0
    bug_count: int = 0
    bug_rate: float = 0.0
    files: List[FileStat] = field(default_factory=list)


# ===== 核心逻辑 =====

def count_lines(filepath: str) -> Tuple[int, int, int]:
    """
    统计文件的：总行数、有效代码行数、空行数、注释行数
    返回 (total_lines, code_lines, blank_lines, comment_lines)
    """
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception:
        return 0, 0, 0, 0

    ext = os.path.splitext(filepath)[1]
    comment_markers = COMMENT_MARKERS.get(ext, ("#",))
    line_comment = comment_markers[0]
    block_comments = comment_markers[1:] if len(comment_markers) > 1 else ()

    total = len(lines)
    blank = 0
    comments = 0
    in_block_comment = False
    block_close = None

    for line in lines:
        stripped = line.strip()

        # 空行
        if not stripped:
            blank += 1
            continue

        # 多行注释处理（Python 的 docstring）
        if in_block_comment:
            comments += 1
            if block_close and block_close in stripped:
                in_block_comment = False
            continue

        # 检查是否开始多行注释
        started_block = False
        for marker in block_comments:
            if stripped.startswith(marker):
                in_block_comment = True
                block_close = marker
                comments += 1
                # 单行多行注释如 """xxx"""
                if stripped.endswith(marker) and len(stripped) > len(marker) * 2:
                    in_block_comment = False
                started_block = True
                break

        if started_block:
            continue

        # 单行注释
        if stripped.startswith(line_comment):
            comments += 1
            continue

        # 有效代码行
    code = total - blank - comments
    return total, code, blank, comments


def scan_directory(directory: str, exclude: set = None) -> List[FileStat]:
    """递归扫描目录下所有代码文件"""
    exclude = exclude or EXCLUDE_DIRS
    stats = []

    for root, dirs, files in os.walk(directory):
        # 过滤排除目录
        dirs[:] = [d for d in dirs if d not in exclude]

        for filename in sorted(files):
            ext = os.path.splitext(filename)[1]
            if ext not in CODE_EXTENSIONS:
                continue

            filepath = os.path.join(root, filename)
            total, code, blank, comments = count_lines(filepath)

            if total == 0:
                continue

            rel_path = os.path.relpath(filepath)
            stat = FileStat(
                path=rel_path,
                total_lines=total,
                code_lines=code,
                blank_lines=blank,
                comment_lines=comments,
            )
            stats.append(stat)

    return stats


def calculate_bug_rate(stats: List[FileStat], bug_count: int, by_lines: bool = True) -> List[FileStat]:
    """
    按代码行数分配 Bug 并计算千行 Bug 率

    by_lines=True  → 按代码行数比例分配 Bug
    by_lines=False → 平均分配 Bug
    """
    total_code = sum(s.code_lines for s in stats)
    if total_code == 0:
        return stats

    remaining_bugs = bug_count
    for i, stat in enumerate(stats):
        if by_lines:
            # 按代码行数比例分配，最后一个文件吸收余数
            if i == len(stats) - 1:
                stat.bug_count = remaining_bugs
            else:
                stat.bug_count = round(stat.code_lines / total_code * bug_count)
                remaining_bugs -= stat.bug_count

            if stat.code_lines > 0:
                stat.bug_rate = stat.bug_count / stat.code_lines * 1000
        else:
            # 平均分配
            if i == len(stats) - 1:
                stat.bug_count = remaining_bugs
            else:
                stat.bug_count = bug_count // len(stats)
                remaining_bugs -= stat.bug_count

            if stat.code_lines > 0:
                stat.bug_rate = stat.bug_count / stat.code_lines * 1000

    return stats


def group_by_module(stats: List[FileStat]) -> Dict[str, ModuleStat]:
    """按一级子目录分组统计"""
    modules: Dict[str, ModuleStat] = {}

    for stat in stats:
        parts = Path(stat.path).parts
        # 取第一个目录作为模块名
        module_name = parts[0] if len(parts) > 1 else os.path.dirname(stat.path) or "根目录"

        if module_name not in modules:
            modules[module_name] = ModuleStat(name=module_name)

        mod = modules[module_name]
        mod.total_files += 1
        mod.total_lines += stat.total_lines
        mod.code_lines += stat.code_lines
        mod.bug_count += stat.bug_count
        mod.files.append(stat)

    # 计算模块级千行 Bug 率
    for mod in modules.values():
        if mod.code_lines > 0:
            mod.bug_rate = mod.bug_count / mod.code_lines * 1000

    return modules


# ===== 输出 =====

def print_summary(stats: List[FileStat], modules: Dict[str, ModuleStat], bug_count: int):
    """打印汇总报告"""
    total_files = len(stats)
    total_code = sum(s.code_lines for s in stats)
    total_blank = sum(s.blank_lines for s in stats)
    total_comments = sum(s.comment_lines for s in stats)
    overall_rate = bug_count / total_code * 1000 if total_code > 0 else 0

    print("=" * 70)
    print(" 📊 千行 Bug 率统计报告")
    print("=" * 70)
    print(f"  Bug 总数:     {bug_count}")
    print(f"  文件总数:     {total_files}")
    print(f"  代码总行数:   {total_code}")
    print(f"  空行数:       {total_blank}")
    print(f"  注释行数:     {total_comments}")
    print(f"  千行 Bug 率:  {overall_rate:.2f}")
    print("=" * 70)

    # 模块级汇总
    if modules:
        print(f"\n {'模块':<30} {'文件数':>6} {'代码行':>8} {'Bug数':>6} {'千行Bug率':>10}")
        print("-" * 70)
        for name, mod in sorted(modules.items()):
            print(f" {name:<30} {mod.total_files:>6} {mod.code_lines:>8} {mod.bug_count:>6} {mod.bug_rate:>10.2f}")
        print("-" * 70)


def print_detail(modules: Dict[str, ModuleStat]):
    """打印文件级明细"""
    print(f"\n {'文件':<55} {'代码行':>7} {'Bug':>4} {'千行Bug率':>10}")
    print("-" * 80)

    for name, mod in sorted(modules.items()):
        print(f"\n  📁 {name}/  (千行Bug率: {mod.bug_rate:.2f})")
        for f in sorted(mod.files, key=lambda x: x.bug_rate, reverse=True):
            rate_str = f"{f.bug_rate:.2f}" if f.bug_count > 0 else "—"
            print(f"    {f.path:<55} {f.code_lines:>7} {f.bug_count:>4} {rate_str:>10}")


# ===== 主入口 =====

def main():
    parser = argparse.ArgumentParser(description="千行 Bug 率自动计算工具")
    parser.add_argument("--dir", default=".", help="要扫描的目录 (默认: 当前目录)")
    parser.add_argument("--bugs", type=int, default=10, help="Bug 总数 (默认: 10)")
    parser.add_argument("--detail", action="store_true", help="显示文件级明细")
    parser.add_argument("--avg", action="store_true", help="Bug 平均分配，不按代码行数比例")
    args = parser.parse_args()

    if not os.path.isdir(args.dir):
        print(f"错误: 目录 '{args.dir}' 不存在")
        sys.exit(1)

    print(f"正在扫描目录: {args.dir}")
    print(f"Bug 总数: {args.bugs}\n")

    # 扫描代码文件
    stats = scan_directory(args.dir)
    if not stats:
        print("未找到任何代码文件")
        sys.exit(0)

    # 分配 Bug 并计算千行 Bug 率
    stats = calculate_bug_rate(stats, args.bugs, by_lines=not args.avg)

    # 按模块分组
    modules = group_by_module(stats)

    # 输出报告
    print_summary(stats, modules, args.bugs)
    if args.detail:
        print_detail(modules)

    print()


if __name__ == "__main__":
    main()
