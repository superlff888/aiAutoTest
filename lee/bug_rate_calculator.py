"""
千行 Bug 率自动计算工具

两种模式：
1. 静态扫描模式：扫描当前目录下所有代码文件的行数，分配 Bug 计算千行 Bug 率
2. Git Diff 模式：对比两个分支/提交的变更行数，基于变更行数计算千行 Bug 率

Git Diff 模式变更量计算（代码行级别）：
  新增行   — master 没有，main 有的代码行（纯新增）
  更新行   — 两个分支都有，但内容被修改的代码行
  删除行   — master 有，main 没有的代码行（纯删除）
  变更总量 = 新增行 + 更新行 + 删除行
  千行 Bug 率 = Bug 数 / 变更总量 * 1000

Usage:
    python bug_rate_calculator.py                          # 静态扫描，10 个 Bug
    python bug_rate_calculator.py --diff master main --bugs 10
    python bug_rate_calculator.py --diff master main --bugs 10 --detail
"""

import argparse
import os
import subprocess
import sys
import io
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# Windows GBK 终端兼容
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


# ===== 配置区 =====

CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs",
    ".rb", ".sh", ".bash", ".php", ".c", ".cpp", ".h", ".cs",
}

EXCLUDE_DIRS = {
    ".git", ".venv", "venv", "__pycache__", "node_modules",
    ".idea", ".vscode", "build", "dist", ".tox",
}

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
    status: str = ""            # A=新增文件, M=修改文件, D=删除文件
    total_lines: int = 0
    code_lines: int = 0
    blank_lines: int = 0
    comment_lines: int = 0
    new_lines: int = 0          # 新增行（纯新加）
    updated_lines: int = 0      # 更新行（内容被修改）
    deleted_lines: int = 0      # 删除行（纯删除）
    bug_count: int = 0
    bug_rate: float = 0.0

    @property
    def changed_lines(self) -> int:
        return self.new_lines + self.updated_lines + self.deleted_lines


@dataclass
class ModuleStat:
    """模块（目录）的统计信息"""
    name: str
    total_files: int = 0
    total_lines: int = 0
    code_lines: int = 0
    new_lines: int = 0
    updated_lines: int = 0
    deleted_lines: int = 0
    bug_count: int = 0
    bug_rate: float = 0.0
    files: List[FileStat] = field(default_factory=list)

    @property
    def changed_lines(self) -> int:
        return self.new_lines + self.updated_lines + self.deleted_lines


# ===== 核心逻辑 =====

def count_lines(filepath: str) -> Tuple[int, int, int, int]:
    """
    统计文件：总行数、有效代码行数、空行数、注释行数
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

        if not stripped:
            blank += 1
            continue

        if in_block_comment:
            comments += 1
            if block_close and block_close in stripped:
                in_block_comment = False
            continue

        started_block = False
        for marker in block_comments:
            if stripped.startswith(marker):
                in_block_comment = True
                block_close = marker
                comments += 1
                if stripped.endswith(marker) and len(stripped) > len(marker) * 2:
                    in_block_comment = False
                started_block = True
                break

        if started_block:
            continue

        if stripped.startswith(line_comment):
            comments += 1
            continue

    code = total - blank - comments
    return total, code, blank, comments


def scan_directory(directory: str, exclude: set = None) -> List[FileStat]:
    """递归扫描目录下所有代码文件"""
    exclude = exclude or EXCLUDE_DIRS
    stats = []

    for root, dirs, files in os.walk(directory):
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


def get_git_diff_stats(base: str, target: str) -> List[FileStat]:
    """
    获取 Git diff 统计：对比 base 和 target 分支，返回每个文件的变更行数
    base   → 基准分支（如 master）
    target → 对比分支（如 main）

    git diff --numstat 对每个文件返回 added 和 deleted：
      - 新增文件：added = 文件总行数, deleted = 0
      - 删除文件：added = 0, deleted = 文件总行数
      - 修改文件：added 和 deleted 分别表示 git 视角的增删

    对每个文件，变更量按 max(added, deleted) 计算：
      更新行 = min(added, deleted)   — 原有行被修改
      新增行 = added - 更新行         — 纯新加的行
      删除行 = deleted - 更新行       — 纯删除的行
      变更量 = 新增 + 更新 + 删除 = max(added, deleted)
    """
    ref = f"{base}...{target}"

    # 1. 获取文件状态（A/M/D/R）
    cmd_status = ["git", "-c", "core.quotePath=false", "diff", "--name-status", ref]
    result = subprocess.run(cmd_status, capture_output=True, text=True, encoding='utf-8')
    if result.returncode != 0:
        print(f"Git 命令执行失败: {' '.join(cmd_status)}")
        print(f"错误信息: {result.stderr}")
        sys.exit(1)

    # 2. 获取增删行数
    cmd_numstat = ["git", "-c", "core.quotePath=false", "diff", "--numstat", ref]
    result2 = subprocess.run(cmd_numstat, capture_output=True, text=True, encoding='utf-8')

    # 构建 numstat 查找表: filepath -> (added, deleted)
    numstat_map: Dict[str, Tuple[int, int]] = {}
    if result2.stdout.strip():
        for line in result2.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) == 3:
                added_str, deleted_str, filepath = parts
                added = int(added_str) if added_str != "-" else 0
                deleted = int(deleted_str) if deleted_str != "-" else 0
                numstat_map[filepath] = (added, deleted)

    stats = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue

        parts = line.split("\t")
        if len(parts) < 2:
            continue

        status = parts[0]

        if status in ("A", "M", "D"):
            filepath = parts[1]
        elif status.startswith("R"):
            if len(parts) >= 3:
                filepath = parts[2]
            else:
                continue
            status = "M"
        else:
            continue

        ext = os.path.splitext(filepath)[1]
        if ext not in CODE_EXTENSIONS:
            continue

        added, deleted = numstat_map.get(filepath, (0, 0))

        updated = min(added, deleted)
        new_only = added - updated
        deleted_only = deleted - updated

        stat = FileStat(
            path=filepath,
            status=status,
            new_lines=new_only,
            updated_lines=updated,
            deleted_lines=deleted_only,
        )
        stats.append(stat)

    return stats


def calculate_bug_rate_by_lines(stats: List[FileStat], bug_count: int) -> List[FileStat]:
    """按变更行数分配 Bug 并计算千行 Bug 率"""
    total_changed = sum(s.changed_lines for s in stats)
    if total_changed == 0:
        return stats

    # 最大余数法分配
    quotients = []
    for stat in stats:
        exact = stat.changed_lines / total_changed * bug_count
        quotients.append((stat, exact, exact - int(exact)))

    remaining = bug_count
    for stat, exact, frac in quotients:
        stat.bug_count = int(exact)
        remaining -= stat.bug_count

    quotients.sort(key=lambda x: x[2], reverse=True)
    for stat, exact, frac in quotients:
        if remaining <= 0:
            break
        stat.bug_count += 1
        remaining -= 1

    for stat in stats:
        if stat.changed_lines > 0:
            stat.bug_rate = stat.bug_count / stat.changed_lines * 1000

    return stats


def calculate_bug_rate_static(stats: List[FileStat], bug_count: int) -> List[FileStat]:
    """静态模式：按代码总行数分配 Bug"""
    total_code = sum(s.code_lines for s in stats)
    if total_code == 0:
        return stats

    quotients = []
    for stat in stats:
        exact = stat.code_lines / total_code * bug_count
        quotients.append((stat, exact, exact - int(exact)))

    remaining = bug_count
    for stat, exact, frac in quotients:
        stat.bug_count = int(exact)
        remaining -= stat.bug_count

    quotients.sort(key=lambda x: x[2], reverse=True)
    for stat, exact, frac in quotients:
        if remaining <= 0:
            break
        stat.bug_count += 1
        remaining -= 1

    for stat in stats:
        if stat.code_lines > 0:
            stat.bug_rate = stat.bug_count / stat.code_lines * 1000

    return stats


def group_by_module(stats: List[FileStat], diff_mode: bool = False) -> Dict[str, ModuleStat]:
    """按一级子目录分组统计"""
    modules: Dict[str, ModuleStat] = {}

    for stat in stats:
        parts = Path(stat.path).parts
        module_name = parts[0] if len(parts) > 1 else os.path.dirname(stat.path) or "根目录"

        if module_name not in modules:
            modules[module_name] = ModuleStat(name=module_name)

        mod = modules[module_name]
        mod.total_files += 1
        mod.total_lines += stat.total_lines
        mod.code_lines += stat.code_lines
        mod.new_lines += stat.new_lines
        mod.updated_lines += stat.updated_lines
        mod.deleted_lines += stat.deleted_lines
        mod.bug_count += stat.bug_count
        mod.files.append(stat)

    for mod in modules.values():
        base = mod.changed_lines if diff_mode else mod.code_lines
        if base > 0:
            mod.bug_rate = mod.bug_count / base * 1000

    return modules


# ===== 输出 =====

def print_static_summary(stats: List[FileStat], modules: Dict[str, ModuleStat], bug_count: int):
    """静态模式汇总报告"""
    total_files = len(stats)
    total_code = sum(s.code_lines for s in stats)
    total_blank = sum(s.blank_lines for s in stats)
    total_comments = sum(s.comment_lines for s in stats)
    overall_rate = bug_count / total_code * 1000 if total_code > 0 else 0

    print("=" * 70)
    print(" [REPORT] 千行 Bug 率统计报告 (静态扫描)")
    print("=" * 70)
    print(f"  Bug 总数:     {bug_count}")
    print(f"  文件总数:     {total_files}")
    print(f"  代码总行数:   {total_code}")
    print(f"  空行数:       {total_blank}")
    print(f"  注释行数:     {total_comments}")
    print(f"  千行 Bug 率:  {overall_rate:.2f}")
    print("=" * 70)

    print(f"\n {'模块':<30} {'文件数':>6} {'代码行':>8} {'Bug数':>6} {'千行Bug率':>10}")
    print("-" * 70)
    for name, mod in sorted(modules.items()):
        print(f" {name:<30} {mod.total_files:>6} {mod.code_lines:>8} {mod.bug_count:>6} {mod.bug_rate:>10.2f}")
    print("-" * 70)


def print_diff_summary(stats: List[FileStat], modules: Dict[str, ModuleStat],
                       bug_count: int, base: str, target: str):
    """Git diff 模式汇总报告"""
    total_files = len(stats)
    total_new = sum(s.new_lines for s in stats)
    total_updated = sum(s.updated_lines for s in stats)
    total_deleted = sum(s.deleted_lines for s in stats)
    total_changed = total_new + total_updated + total_deleted
    overall_rate = bug_count / total_changed * 1000 if total_changed > 0 else 0

    print("=" * 75)
    print(f" [REPORT] 千行 Bug 率统计报告 (Git Diff: {base} -> {target})")
    print("=" * 75)
    print(f"  Bug 总数:           {bug_count}")
    print(f"  变更文件数:         {total_files}")
    print(f"  新增行:             {total_new}")
    print(f"  更新行:             {total_updated}")
    print(f"  删除行:             {total_deleted}")
    print(f"  变更总行数:         {total_changed}")
    print(f"  千行 Bug 率:        {overall_rate:.2f}")
    print("=" * 75)

    hdr = f" {'模块':<25} {'新增行':>6} {'更新行':>6} {'删除行':>6} {'Bug':>4} {'千行Bug率':>10}"
    print(hdr)
    print("-" * len(hdr.split("\n")[0]))
    for name, mod in sorted(modules.items()):
        row = (f" {name:<25} {mod.new_lines:>6} {mod.updated_lines:>6}"
               f" {mod.deleted_lines:>6} {mod.bug_count:>4} {mod.bug_rate:>10.2f}")
        print(row)
    print("-" * len(hdr.split("\n")[0]))


STATUS_LABEL = {"A": "新增", "M": "修改", "D": "删除"}


def print_detail(modules: Dict[str, ModuleStat], diff_mode: bool = False):
    """打印文件级明细"""
    if diff_mode:
        print(f"\n {'文件':<45} {'状态':>6} {'新增行':>6} {'更新行':>6} {'删除行':>6} {'Bug':>4} {'千行Bug率':>10}")
    else:
        print(f"\n {'文件':<55} {'代码行':>7} {'Bug':>4} {'千行Bug率':>10}")
    print("-" * 95)

    for name, mod in sorted(modules.items()):
        print(f"\n  [DIR] {name}/  (千行Bug率: {mod.bug_rate:.2f})")
        for f in sorted(mod.files, key=lambda x: x.bug_rate, reverse=True):
            rate_str = f"{f.bug_rate:.2f}" if f.bug_count > 0 else "—"
            if diff_mode:
                label = STATUS_LABEL.get(f.status, f.status)
                print(f"    {f.path:<45} {label:>6} {f.new_lines:>6} {f.updated_lines:>6} {f.deleted_lines:>6} {f.bug_count:>4} {rate_str:>10}")
            else:
                print(f"    {f.path:<55} {f.code_lines:>7} {f.bug_count:>4} {rate_str:>10}")


# ===== 主入口 =====

def main():
    parser = argparse.ArgumentParser(
        description="千行 Bug 率自动计算工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 静态扫描当前目录
  python bug_rate_calculator.py --bugs 10

  # 对比 master 和 main 分支的变更
  python bug_rate_calculator.py --diff master main --bugs 10

  # 对比最近5次提交
  python bug_rate_calculator.py --diff HEAD~5 HEAD --bugs 3
        """,
    )
    parser.add_argument("--dir", default=".", help="要扫描的目录 (默认: 当前目录)")
    parser.add_argument("--bugs", type=int, default=10, help="Bug 总数 (默认: 10)")
    parser.add_argument("--detail", action="store_true", help="显示文件级明细")
    parser.add_argument(
        "--diff", nargs=2, metavar=("BASE", "TARGET"),
        help="Git Diff 模式：对比 BASE 和 TARGET 分支/提交 "
             "(例: --diff master main)"
    )
    args = parser.parse_args()

    # Git Diff 模式
    if args.diff:
        base, target = args.diff
        print(f"Git Diff 模式: {base} -> {target}")
        print(f"Bug 总数: {args.bugs}\n")

        stats = get_git_diff_stats(base, target)
        if not stats:
            print("未找到代码变更文件")
            sys.exit(0)

        stats = calculate_bug_rate_by_lines(stats, args.bugs)
        modules = group_by_module(stats, diff_mode=True)

        print_diff_summary(stats, modules, args.bugs, base, target)
        if args.detail:
            print_detail(modules, diff_mode=True)
    else:
        # 静态扫描模式
        if not os.path.isdir(args.dir):
            print(f"错误: 目录 '{args.dir}' 不存在")
            sys.exit(1)

        print(f"静态扫描模式: {args.dir}")
        print(f"Bug 总数: {args.bugs}\n")

        stats = scan_directory(args.dir)
        if not stats:
            print("未找到任何代码文件")
            sys.exit(0)

        stats = calculate_bug_rate_static(stats, args.bugs)
        modules = group_by_module(stats)

        print_static_summary(stats, modules, args.bugs)
        if args.detail:
            print_detail(modules)

    print()


if __name__ == "__main__":
    main()
